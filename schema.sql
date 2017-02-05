-- schema.sql
USE mysql;

CREATE USER 'lichenxi'@'localhost' IDENTIFIED BY 'Lichenxi20000110';

FLUSH PRIVILEGES;

DROP DATABASE IF EXISTS awesome;

CREATE DATABASE awesome;

USE awesome;

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON awesome.* TO 'lichenxi'@'localhost'
IDENTIFIED BY 'Lichenxi20000110';

CREATE TABLE users (
  `id`         VARCHAR(50)  NOT NULL,
  `email`      VARCHAR(50)  NOT NULL,
  `password`   VARCHAR(50)  NOT NULL,
  `admin`      BOOL         NOT NULL,
  `name`      VARCHAR(50)  NOT NULL,
  `image`      VARCHAR(500) NOT NULL,
  `created_at` REAL         NOT NULL,
  UNIQUE KEY `idx_email` (`email`),
  KEY `idx_created_at` (`created_at`),
  PRIMARY KEY (`id`)
)
  ENGINE = innodb
  DEFAULT CHARSET = utf8;

CREATE TABLE blogs (
  `id`         VARCHAR(50)  NOT NULL,
  `user_id`    VARCHAR(50)  NOT NULL,
  `user_name`  VARCHAR(50)  NOT NULL,
  `user_image` VARCHAR(500) NOT NULL,
  `name`       VARCHAR(50)  NOT NULL,
  `summary`    VARCHAR(200) NOT NULL,
  `content`    MEDIUMTEXT   NOT NULL,
  `created_at` REAL         NOT NULL,
  KEY `idx_created_at` (`created_at`),
  PRIMARY KEY (`id`)
)
  ENGINE = innodb
  DEFAULT CHARSET = utf8;

CREATE TABLE comments (
  `id` VARCHAR(50) NOT NULL ,
  `blog_id` VARCHAR(50) NOT NULL ,
  `user_id`    VARCHAR(50)  NOT NULL,
  `user_name`  VARCHAR(50)  NOT NULL,
  `user_image` VARCHAR(500) NOT NULL,
  `content`    MEDIUMTEXT   NOT NULL,
  `created_at` REAL         NOT NULL,
  KEY `idx_created_at` (`created_at`),
  PRIMARY KEY (`id`)
)
  ENGINE = innodb
  DEFAULT CHARSET = utf8;
