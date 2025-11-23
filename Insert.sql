-- Tag
INSERT INTO Tag (TagName, Type) 
VALUES 
('电气工程学院', 0),
('自动化与感知学院', 0),
('计算机学院', 0),
('集成电路学院', 0),
('教务处', 0),
('微信公众号', 0),
('考试信息', 1),
('科学研究', 1),
('文体活动', 1),
('党建工作', 1),
('学生事务', 1),
('课程安排', 1),
('师生成就', 1);

-- 查看
SELECT * FROM Tag;

-- 插入新闻（示例）
INSERT INTO News(PublishDate, URL, Summary)
VALUES
('2025-04-23', 'https://mp.weixin.qq.com/s/_JbG3gKpknNy2k9uc2t_OA', '喜报！电气学子李辰在第二届全国大学生职业规划大赛总决赛斩获金奖');

INSERT INTO News(PublishDate, URL, Summary)
VALUES
('2025-05-11', 'https://mp.weixin.qq.com/s/8Kl6XXJJrvRrdUf7wloC-A', '今天，正式成立！交大新学院+1');

INSERT INTO News(PublishDate, URL, Summary)
VALUES
('2025-10-15', 'https://cs.sjtu.edu.cn/xshd/1038.html', 'The Technological Imperative for Ethical Evolution');

-- 插入用户喜好标签
INSERT INTO User_Tag(UserID, TagID, VisitTimes)
VALUES
(1,13,1);

SELECT DISTINCT nt.NewsID FROM News_Tag nt WHERE nt.TagID IN (SELECT TagID FROM User_Tag WHERE UserID = 1);