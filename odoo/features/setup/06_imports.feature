# -*- coding: utf-8 -*-
@depiltech @setup

Feature: Parameter the new database
  In order to have a coherent installation
  I've automated the manual steps.
  @csv_import
  Scenario: import csv
    Given "survey.survey" is imported from CSV "setup/survey.survey.csv" using delimiter ","

  @csv_import
  Scenario: import csv
    Given "survey.page" is imported from CSV "setup/survey.page.csv" using delimiter ","

  @csv_import
  Scenario: import csv
    Given "survey.question" is imported from CSV "setup/survey.question.csv" using delimiter ","

  @csv_import_warehouse
  Scenario: import csv
    Given "stock.warehouse" is imported from CSV "setup/stock.warehouse.csv" using delimiter ","

  @csv_import_product_category
  Scenario: import csv
    Given "product.category" is imported from CSV "setup/product.category.csv" using delimiter ";"

  @csv_import_product
  Scenario: import csv
    Given "product.product" is imported from CSV "setup/product.csv" using delimiter ";"

  # tax are managed in anthem songs

