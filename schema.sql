-- Hospital Patient Data Analysis System
-- Run in MySQL Workbench. Uses synthetic/demo data only.
CREATE DATABASE IF NOT EXISTS hospital_patient_data_analysis_system;
USE hospital_patient_data_analysis_system;
CREATE TABLE IF NOT EXISTS visits (
    visit_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(40) NOT NULL,
    department VARCHAR(100) NOT NULL,
    visit_date DATE NOT NULL,
    visit_type VARCHAR(60),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS patients (
    patient_code VARCHAR(40) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Preserve patient codes already present in visits when upgrading an existing database.
INSERT IGNORE INTO patients (patient_code)
SELECT DISTINCT patient_code FROM visits
WHERE patient_code IS NOT NULL AND patient_code <> '';
