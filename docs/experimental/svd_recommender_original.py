"""Original SVD prototype from a teammate's experimental drop.

ARCHIVAL ONLY — this file is NOT imported by the running app.

This is the starting point we adapted into `recommenders/user_based.py` (V2A).
Kept here for the defense presentation so we can show the iteration from
prototype to production.

Differences between this prototype and the V2A production module:

1. ID bridge
   - Prototype: bridges MovieLens movieId -> imdbId via links.csv.
   - V2A:       bridges MovieLens movieId -> tmdbId directly, because every
                other surface in the Flask app (catalog, recommendations,
                routes) keys off TMDB ids. Avoids an extra IMDB hop.

2. Data sampling
   - Prototype: `data_df.sample(frac=0.05, random_state=42)` — trains on 5%
                of the ratings, hard-coded.
   - V2A:       trains on the full 39,542-row bridged set. No sampling.

3. Time filter
   - Prototype: drops ratings after 2006-07-19, a hardcoded train/test split.
   - V2A:       uses the full ratings_clean.csv timeline; the eval script
                does its own 80/20 random split.

4. Rating centering
   - Prototype: feeds raw ratings into svds(). Predictions skew toward
                popular/highly-rated movies regardless of the user's taste.
   - V2A:       subtracts each user's mean rating before factorization, adds
                it back at serving time, then clips to [0.5, 5.0]. This is
                the standard preprocessing step that lets SVD pick up each
                user's deviation from their personal baseline rather than
                the global popularity signal.

5. Persistence
   - Prototype: pickles the trained model to disk.
   - V2A:       trains at app startup in <1 second; no persistence needed
                given the dataset size (671 users x 1956 movies).

6. Serving shape
   - Prototype: returns (imdbId, score) tuples.
   - V2A:       returns Reelvana movie_to_list_dict() shapes so the JSON
                matches V1's /api/recommend/<movie_id> and the existing
                frontend renderMovieCard() works unchanged.
"""
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
import pickle
import os

class SVDMovieRecommender:
    def __init__(self, n_factors=50):
        self.K = n_factors
        self.user_mapper = None
        self.movie_mapper = None
        self.user_inv_mapper = None
        self.movie_inv_mapper = None
        self.R = None
        self.all_user_predicted_ratings = None

    def _prepare_data(self, data_df):
        # 电影版直接用rating，不需要log转换
        data_df = data_df[data_df['rating'] > 0]
        data_df['userId']  = data_df['userId'].astype(str).astype('category')
        data_df['movieId'] = data_df['movieId'].astype(str).astype('category')

        self.user_mapper     = {u: i for i, u in enumerate(data_df['userId'].cat.categories)}
        self.movie_mapper    = {m: i for i, m in enumerate(data_df['movieId'].cat.categories)}
        self.user_inv_mapper  = {i: u for u, i in self.user_mapper.items()}
        self.movie_inv_mapper = {i: m for m, i in self.movie_mapper.items()}

        data_df['user_index']  = data_df['userId'].cat.codes
        data_df['movie_index'] = data_df['movieId'].cat.codes

        return data_df

    def fit(self, ratings_path, links_path):
        print("加载数据...")
        data_df = pd.read_csv(ratings_path)
        data_df['timestamp'] = pd.to_datetime(data_df['timestamp'], unit='s')

        # 用links.csv把movieId转成imdbId
        links = pd.read_csv(links_path).dropna(subset=['imdbId'])
        links['imdbId'] = links['imdbId'].astype(int).astype(str)
        ml_to_imdb = dict(zip(links['movieId'].astype(str), links['imdbId']))
        data_df['movieId'] = data_df['movieId'].astype(str).map(ml_to_imdb)
        data_df = data_df.dropna(subset=['movieId'])

        # 只用训练集时间范围内的数据
        split_ts = pd.Timestamp('2006-07-19')
        data_df  = data_df[data_df['timestamp'] <= split_ts]
        data_df  = data_df.sample(frac=0.05, random_state=42)
        print(f"   采样后条数: {len(data_df)}")

        data_df = self._prepare_data(data_df)
        print(f"   用户数: {len(self.user_mapper)}, 电影数: {len(self.movie_mapper)}")

        self.R = csr_matrix((
            data_df['rating'],
            (data_df['user_index'], data_df['movie_index'])
        ))

        print("SVD矩阵分解中（可能需要几分钟）...")
        U, sigma, Vt = svds(self.R, k=self.K)
        sigma = np.diag(sigma)
        self.all_user_predicted_ratings = np.dot(np.dot(U, sigma), Vt)
        print("训练完成！")

    def recommend(self, user_id, num_recommendations=10):
        user_id = str(user_id)
        if user_id not in self.user_mapper:
            return f"userId {user_id} 不在训练集中"

        user_index = self.user_mapper[user_id]
        predicted  = self.all_user_predicted_ratings[user_index].copy()

        # 排除已看过的
        seen_indices = self.R[user_index, :].nonzero()[1]
        predicted[seen_indices] = -np.inf

        top_indices = predicted.argsort()[::-1][:num_recommendations]
        return [(self.movie_inv_mapper[i], predicted[i]) for i in top_indices]

    def save_model(self, filename='movie_svd_model.pkl'):
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"模型已保存: {filename}")


def load_model(filename='movie_svd_model.pkl'):
    if not os.path.exists(filename):
        print(f"找不到文件: {filename}")
        return None
    with open(filename, 'rb') as f:
        model = pickle.load(f)
    print(f"模型加载成功: {filename}")
    return model


# ============================================================
# 主流程
# ============================================================
if __name__ == '__main__':
    RATINGS_PATH = 'ratings.csv'
    LINKS_PATH   = 'links.csv'

    recommender = SVDMovieRecommender(n_factors=50)
    recommender.fit(RATINGS_PATH, LINKS_PATH)
    recommender.save_model('movie_svd_model.pkl')

    # 测试
    loaded = load_model('movie_svd_model.pkl')
    if loaded:
        test_df  = pd.read_csv(RATINGS_PATH)
        test_uid = str(test_df['userId'].sample(1).iloc[0])
        print(f"\n用户 {test_uid} 的推荐结果:")
        recs = loaded.recommend(test_uid, num_recommendations=5)
        if isinstance(recs, str):
            print(recs)
        else:
            for imdb_id, score in recs:
                print(f"   imdbId: {imdb_id} | 预测评分: {score:.4f}")
