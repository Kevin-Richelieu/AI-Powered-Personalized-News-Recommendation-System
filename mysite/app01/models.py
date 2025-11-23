from django.db import models

class User(models.Model):
    userid = models.AutoField(db_column='UserID', primary_key=True)  # Field name made lowercase.
    username = models.CharField(db_column='UserName', unique=True, max_length=50)  # Field name made lowercase.
    password = models.CharField(db_column='PassWord', max_length=50)  # Field name made lowercase.
    major = models.CharField(db_column='Major', max_length=20, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'User'

class News(models.Model):
    newsid = models.AutoField(db_column='NewsID', primary_key=True)  # Field name made lowercase.
    publishdate = models.DateField(db_column='PublishDate')  # Field name made lowercase.
    url = models.CharField(db_column='URL', max_length=100)  # Field name made lowercase.
    summary = models.CharField(db_column='Summary', max_length=300)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'News'

class Tag(models.Model):
    tagid = models.AutoField(db_column='TagID', primary_key=True)  # Field name made lowercase.
    tagname = models.CharField(db_column='TagName', unique=True, max_length=50)  # Field name made lowercase.
    type = models.IntegerField(db_column='Type')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Tag'

class NewsTag(models.Model):
    news = models.ForeignKey(News, models.DO_NOTHING, db_column='NewsID')  # Field name made lowercase.
    tag = models.ForeignKey(Tag, models.DO_NOTHING, db_column='TagID')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'News_Tag'
        unique_together = (('news', 'tag'),)

class UserTag(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='UserID')  # Field name made lowercase.
    tag = models.ForeignKey(Tag, models.DO_NOTHING, db_column='TagID')  # Field name made lowercase.
    visittimes = models.IntegerField(db_column='VisitTimes')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'User_Tag'
        unique_together = (('user', 'tag'),)