# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import models


class Milk(models.Model):
    milk_name = models.CharField(max_length=100)


class Cheese(models.Model):
    cheese_name = models.CharField(max_length=100)


class Recipe(models.Model):
    cheese = models.ForeignKey(Cheese)
    milk = models.ForeignKey(Milk)
    salt = models.BooleanField()


class OtherIngredient(models.Model):
    recipe = models.ForeignKey(Recipe)
    ingredient_name = models.CharField(max_length=100)
