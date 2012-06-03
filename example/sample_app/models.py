from django.db import models


class GroupType(models.Model):
	name = models.CharField(max_length=40)
	
	def __unicode__(self):
		return self.name


class Group(models.Model):
	name = models.CharField(max_length=40)
	g_type = models.ForeignKey(GroupType)
	
	def __unicode__(self):
		return self.name


class Person(models.Model):
	first_name = models.CharField(max_length=20)
	last_name = models.CharField(max_length=20)
	sex = models.CharField(max_length=1, choices=(('m', 'Male'), ('f', 'Female')))
	groups = models.ManyToManyField(Group)
	
	def __unicode__(self):
		return u"%s %s" % (self.first_name, self.last_name)
	

