import pandas as pd

print("📦 加载数据...")
ratings = pd.read_csv('ratings.csv')
links   = pd.read_csv('links.csv').dropna(subset=['imdbId'])
links['imdbId'] = links['imdbId'].astype(int).astype(str)

ml_to_imdb = dict(zip(links['movieId'], links['imdbId']))

print("🔧 转换movieId → imdbId...")
ratings['imdbId'] = ratings['movieId'].map(ml_to_imdb)
ratings = ratings.dropna(subset=['imdbId'])
ratings = ratings.drop(columns=['movieId'])

# 调整列顺序
ratings = ratings[['userId', 'imdbId', 'rating', 'timestamp']]

print(f"   原始条数: 26024289")
print(f"   转换后条数: {len(ratings)}")

ratings.to_csv('ratings_imdb.csv', index=False)
print("✅ 已保存: ratings_imdb.csv")