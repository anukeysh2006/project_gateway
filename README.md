# Project Gateway – Supplier Onboarding & Qualification  

## 📌 Overview  
**Project Gateway** is a backend service designed for **supplier onboarding and qualification** at Innovate Robotics.  
It ensures every supplier follows a structured **4-stage digital thread** from application submission to activation,  
providing transparency, automation, and auditability.  

---

## 🔄 Supplier Onboarding Lifecycle  

1. **PENDING_REVIEW** → Supplier submits an application.  
2. **AUDIT_SCHEDULED** → System automatically schedules an audit.  
3. **AUDIT_PASSED** → Audit result recorded (currently automated as *pass*).  
4. **ACTIVE** → Supplier activated and assigned a system-generated Supplier ID.  

Every transition is stored in a **single MongoDB document**, maintaining the complete history for traceability.  

---

## ⚙️ Tech Stack  

- **Language/Framework**: Python, FastAPI  
- **Event Streaming**: Apache Kafka  
- **Database**: MongoDB  
- **Orchestration**: Kafka Topics + Automated Consumer  
- **Deployment**: Docker & Docker Compose  

---

## 🚀 Features
- Manual trigger for initial supplier application submission.  
- Automatic progression through all onboarding phases.  
- Event-driven architecture using Kafka topics.  
  

---


