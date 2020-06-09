# 星巴克项目 StarbucksCapstoneChallenge


### 项目描述:
这个数据集是模拟 Starbucks rewards 移动 app 上，某一种饮品的推送和用户消费数据。
之所以选择练习该项目，是因为这类业务逻辑在电商、广告、内容、O2O等领域是比较相似和通用的，方法可以直接应用到工作中。

依赖的库：
- pandas
- numpy
- matplotlib.pyplot 
- seaborn
- json
- statsmodels.api

### 业务背景
每隔几天，星巴克会向 app 的用户发送一些推送，这个推送可能是饮品的广告、折扣券或 BOGO（买一送一）。

顾客收到的推送可能是不同的，一些顾客可能一连几周都收不到任何推送。
每种推送都有有效期，可以认为顾客在有效期内都可能受到这条推送的影响。
也有可能顾客购买了商品，但没有收到或者没有看推送。

数据集中还包含 app 上支付的交易信息，交易信息包括购买时间和购买支付的金额。交易信息还包括该顾客收到的推送种类和数量以及看了该推送的时间。顾客做出了购买行为也会产生一条记录。

本项目希望将交易数据、人口统计数据和推送数据结合起来，分析哪一类人群会受到某种推送的影响。
暂时主要使用分类对比分析的方法。

### 文件描述

#### data，包含三个数据文件
1. portfolio.json – 包括推送的 id 和每个推送的元数据（持续时间、种类等等）
2. profile.json – 每个顾客的人口统计数据
3. transcript.json – 交易、收到的推送、查看的推送和完成的推送的记录

以下是文件中每个变量的类型和解释 ：
1. portfolio.json

- id (string) – 推送的id
- offer_type (string) – 推送的种类，例如 BOGO、打折（discount）、信息（informational）
- difficulty (int) – 满足推送的要求所需的最少花费
- reward (int) – 满足推送的要求后给与的优惠
- duration (int) – 推送持续的时间，单位是天
- channels (字符串列表)

2. profile.json

- age (int) – 顾客的年龄
- became_member_on (int) – 该顾客第一次注册app的时间
- gender (str) – 顾客的性别（注意除了表示男性的 M 和表示女性的 F 之外，还有表示其他的 O）
- id (str) – 顾客id
- income (float) – 顾客的收入

3. transcript.json

- event (str) – 记录的描述（比如交易记录、推送已收到、推送已阅）
- person (str) – 顾客id
- time (int) – 单位是小时，测试开始时计时。该数据从时间点 t=0 开始
- value - (dict of strings) – 推送的id 或者交易的数额

#### clean_data.py 
包括所有数据清洗函数，主要函数功能：
- clean_portfolio：清洗portfolio活动offer信息
- clean_profile：清洗profile用户信息
- draw_hist_pics：遍历数据列，画直方图，默认用颜色区分性别
- parse_offer：清洗交易数据记录transcript里的value字段
- sep_df：分离交易记录表里的四类记录数据，包括接收offer、浏览offer、完成offer，以及所有交易金额记录
- is_valid_viewed：判断是否为有效浏览
- is_valid_comp：判断消费是否受到offer影响,也即按照业务逻辑，offer是否真正完成
- clean_response：主要输出每个发出的offer是否真正完成/被响应的标识，包括接收记录+响应标识，和交易记录+是否活动交易+活动offer等明细记录
- clean_cid_stats：输出用户的offer接收、交易记录统计数据
- add_feature_cols：计算用户对活动要素的偏好指标
- find_cid_groups：查看特定偏好的用户群数据，发现用户群特征


#### Starbucks_Capstone_notebook-zh.ipynb 
数据探索和分析notebook，主要过程和分析描述见：<https://www.jianshu.com/p/971ea4e96fd0> 
