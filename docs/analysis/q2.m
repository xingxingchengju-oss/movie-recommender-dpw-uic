%% RQ2: 财务成功因素分析 (Budget, Revenue, ROI)

% 1. 提取有效财务数据 (剔除 Budget 或 Revenue 为空/0 的行)
% 注意：根据你的清洗逻辑，无效值现在应该是 NaN 或 0
df_fin = df(~(isnan(df.budget) | isnan(df.revenue) | df.budget == 0 | df.revenue == 0), :);

%% --- 1. 预算与收入的关系 (散点图 + 回归线) ---
figure('Color', 'w', 'Name', 'Budget vs Revenue Regression');
scatter(df_fin.budget, df_fin.revenue, 15, 'filled', 'MarkerFaceAlpha', 0.3);
hold on;

% 计算线性回归线
p = polyfit(df_fin.budget, df_fin.revenue, 1);
yfit = polyval(p, df_fin.budget);
plot(df_fin.budget, yfit, 'r-', 'LineWidth', 2);

xlabel('Budget ($)');
ylabel('Revenue ($)');
title(sprintf('Correlation: Budget vs Revenue (Slope: %.2f)', p(1)));
grid on;
legend('Movies', 'Trend Line');

%% --- 2. 投资回报率分析 (ROI 箱线图) ---
figure('Color', 'w', 'Name', 'ROI by Genre');
% 为了让图表好看，剔除 ROI 的极端离群值 (比如 ROI > 50 的电影)
df_roi = df_fin(df_fin.roi < 50, :); 

% 选取主要类型进行对比
df_roi_sub = df_roi(ismember(string(df_roi.primary_genre), string(top_genres)), :);

boxplot(df_roi_sub.roi, string(df_roi_sub.primary_genre));
ylabel('Return on Investment (ROI)');
title('ROI Distribution across Major Genres');
xtickangle(45);

%% --- 3. 相关性热力图 (Correlation Matrix) ---
figure('Color', 'w', 'Name', 'Financial Correlation');
% 选取数值型指标
num_vars = [df_fin.budget, df_fin.revenue, df_fin.profit, df_fin.roi, df_fin.runtime];
var_names = {'Budget', 'Revenue', 'Profit', 'ROI', 'Runtime'};
corr_matrix = corr(num_vars, 'Rows', 'complete');

h2 = heatmap(var_names, var_names, corr_matrix);
h2.Title = 'Correlation Heatmap of Financial Metrics';
h2.Colormap = hot;