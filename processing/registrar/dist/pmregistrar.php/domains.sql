-- MySQL dump 10.14  Distrib 5.5.41-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: domains
-- ------------------------------------------------------
-- Server version	5.5.41-MariaDB-1ubuntu0.14.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `contact`
--

DROP TABLE IF EXISTS `contact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contact` (
  `id` varchar(8) NOT NULL,
  `firstname` varchar(255) DEFAULT NULL,
  `middlename` varchar(255) DEFAULT NULL,
  `lastname` varchar(255) DEFAULT NULL,
  `password` varchar(8) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `contact`
--

LOCK TABLES `contact` WRITE;
/*!40000 ALTER TABLE `contact` DISABLE KEYS */;
INSERT INTO `contact` VALUES ('3uXZyJA8','vyiayivayiva','yivayivayiva','yivayivayiv','QnAechaR'),('DVucqHoU','vyiayivayiva','yivayivayiva','yivayivayiv','dzjaCAKG'),('4HFCrfLh','vyiayivayiva','yivayivayiva','yivayivayiv','DmwPDGGg'),('Bbs2SQW6','vyiayivayiva','yivayivayiva','yivayivayiv','qgh2Q1IU'),('Iox9Ejrh','vyiayivayiva','yivayivayiva','yivayivayiv','FX6iENzg');
/*!40000 ALTER TABLE `contact` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `domain`
--

DROP TABLE IF EXISTS `domain`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `domain` (
  `name` varchar(64) DEFAULT NULL,
  `status` varchar(16) DEFAULT 'active',
  `customer` varchar(8) NOT NULL,
  `owner` varchar(8) NOT NULL,
  `admin` varchar(8) NOT NULL,
  `bill` varchar(8) NOT NULL,
  `tech` varchar(8) NOT NULL,
  `expiredate` date NOT NULL,
  `ns` text,
  `description` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `domain`
--

LOCK TABLES `domain` WRITE;
/*!40000 ALTER TABLE `domain` DISABLE KEYS */;
INSERT INTO `domain` VALUES ('xxx.my','deleted','3uXZyJA8','DVucqHoU','4HFCrfLh','Bbs2SQW6','Iox9Ejrh','2016-05-27','',''),('xxx.my','deleted','3uXZyJA8','DVucqHoU','4HFCrfLh','Bbs2SQW6','Iox9Ejrh','2016-05-27','',''),('xxx.my','active','3uXZyJA8','DVucqHoU','4HFCrfLh','Bbs2SQW6','Iox9Ejrh','2017-05-27','ns1.ya.com ns2.ya.com ','XX YY UU');
/*!40000 ALTER TABLE `domain` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-05-27 18:09:55