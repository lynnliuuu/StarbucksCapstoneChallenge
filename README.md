# StarbucksCapstoneChallenge


### Project Description:
这个数据集是模拟Starbucks rewards移动app上用户行为的数据。每隔几天，星巴克会向app的用户发送一些推送。这个推送可能仅仅是一条饮品的广告或者是折扣券或 BOGO（买一送一）。一些顾客可能一连几周都收不到任何推送。

分析任务：将交易数据、人口统计数据和推送数据结合起来，判断哪一类人群会受到某种推送的影响。

### 文件描述

#### data，包含三个数据文件
1. portfolio.json – 包括推送的 id 和每个推送的元数据（持续时间、种类等等）
2. profile.json – 每个顾客的人口统计数据
3. transcript.json – 交易、收到的推送、查看的推送和完成的推送的记录

#### 以下是文件中每个变量的类型和解释 ：
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
- transcript.json

3. event (str) – 记录的描述（比如交易记录、推送已收到、推送已阅）
- person (str) – 顾客id
- time (int) – 单位是小时，测试开始时计时。该数据从时间点 t=0 开始
- value - (dict of strings) – 推送的id 或者交易的数额

#### clean_data.py 
包括所有数据清洗函数

#### Starbucks_Capstone_notebook-zh.ipynb 
数据探索和分析
