%% RQ1: 电影发展趋势与类型分布分析
% 假设你已经将 movies_final_clean.csv 导入为 table 格式

% 1. 读取数据
opts = detectImportOptions('movies_final_clean.csv');
df = readtable('movies_final_clean.csv', opts);

% 确保 release_decade 是分类变量或字符串，方便分组
if isnumeric(df.release_decade)
    df.release_decade = string(df.release_decade) + "s";
end

%% --- 1. 电影总产量趋势 (折线图) ---
figure('Color', 'w', 'Name', 'Movie Production Trend');
decade_counts = groupsummary(df, 'release_decade');
plot(categorical(decade_counts.release_decade), decade_counts.GroupCount, ...
    '-o', 'LineWidth', 2, 'MarkerSize', 8, 'Color', [0 0.4470 0.7410]);
grid on;
title('Total Movie Production by Decade (Up to 2017)', 'FontSize', 14);
xlabel('Decade');
ylabel('Number of Movies');

%% --- 2. 电影类型分布演变 (堆叠面积图) ---
% 我们选取排名前 8 的主要类型进行展示，否则图表会太乱
top_genres = {'Drama', 'Comedy', 'Thriller', 'Action', 'Romance', 'Horror', 'Adventure', 'Documentary'};
% 过滤数据，只保留这些主要类型
% 强制转换为字符串数组再对比
df_top = df(ismember(string(df.primary_genre), string(top_genres)), :);

% 创建交叉表：行是年代，列是类型
[G, D, P] = findgroups(df_top.release_decade, df_top.primary_genre);
T = table(D, P, 'VariableNames', {'Decade', 'Genre'});
T.Count = ones(size(D));
summary_T = groupsummary(T, {'Decade', 'Genre'}, 'sum', 'Count');

% 转换为矩阵格式绘图
decades_list = unique(df_top.release_decade);
plot_data = zeros(length(decades_list), length(top_genres));

for i = 1:length(decades_list)
    for j = 1:length(top_genres)
        idx = strcmp(summary_T.Decade, decades_list{i}) & strcmp(summary_T.Genre, top_genres{j});
        if any(idx)
            plot_data(i, j) = summary_T.sum_Count(idx);
        end
    end
end

figure('Color', 'w', 'Name', 'Genre Distribution Area Chart');
area(categorical(decades_list), plot_data);
legend(top_genres, 'Location', 'northwest', 'NumColumns', 2);
title('Evolution of Movie Genres by Decade', 'FontSize', 14);
xlabel('Decade');
ylabel('Number of Movies');
colormap(summer); % 使用清新的配色

%% --- 3. 类型与年代关联热力图 ---
figure('Color', 'w', 'Name', 'Genre-Decade Heatmap');
% 归一化处理（按年代看各类型的占比情况）
plot_data_norm = plot_data ./ sum(plot_data, 2);

h = heatmap(top_genres, decades_list, plot_data_norm);
h.Title = 'Heatmap of Genre Popularity per Decade (Normalized)';
h.XLabel = 'Movie Genre';
h.YLabel = 'Decade';
h.Colormap = sky;