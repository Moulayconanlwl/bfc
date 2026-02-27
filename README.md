# BFC Access Review – Documentation

A Flask-based web application that processes an uploaded Excel file, groups data by owner, allows interactive row‑level decisions (keep/remove), and exports the results.

---

## 🚀 Project Overview

This application:

- Accepts an **Excel (.xlsx)** file upload  
- Reads and validates a required column: **"Data entry filter owner"**
- Groups the rows by owner and returns statistics  
- Displays rows by owner or full dataset  
- Allows **per‑row** or **bulk** decisions (keep/remove)  
- Exports final data into a generated Excel file  
- Uses an in‑memory session store (dictionary)

---

## 📂 Project Structure

Recommended layout:

```
project/
│ app.py
│ README.md
│
├── templates/
│      index.html
│
├── static/
│      getsitelogo.png
│
└── uploads/
```

👉 **Images must be placed in `/static/`**, not `/templates/`.

---

## 🛠 Installation

```
pip install flask pandas openpyxl werkzeug
```

---

## ▶️ Running the Application

```
python app.py
```

The app runs at:

```
http://127.0.0.1:5000/
```

---

## 📘 API Documentation

### **GET /**
Loads the main web interface.

---

### **POST /upload**
Uploads and processes the Excel file.

#### Requirements:
- Must be `.xlsx`
- Must contain `Data entry filter owner`

#### Sample Response:
```json
{
  "success": true,
  "session_id": "20260217100522012345",
  "owners": [
    {"Data entry filter owner": "John", "count": 42}
  ],
  "total_rows": 130
}
```

---

### **GET /get_all_rows/<session_id>**
Returns every row with its decision.

---

### **GET /get_rows/<session_id>/<owner>**
Returns only rows belonging to a specific owner.

---

### **POST /update_decision**
Updates decision for a single row.

Payload:
```json
{
  "session_id": "...",
  "row_index": 10,
  "decision": "remove"
}
```

---

### **POST /bulk_update**
Applies a decision to multiple rows.

Payload:
```json
{
  "session_id": "...",
  "indices": [1,2,3],
  "decision": "keep"
}
```

---

### **GET/POST /export/<session_id>**
Exports the dataset with decisions applied.

---

### **GET /stats/<session_id>**
Returns decision statistics.

Response:
```json
{
  "success": true,
  "total": 200,
  "keep": 150,
  "remove": 50
}
```

---

## ✔ How to Use (User Guide)

1. Start the server and open:
   ```
   http://127.0.0.1:5000/
   ```
2. Upload an Excel file.
3. Choose an owner to filter rows.
4. Mark rows as **keep** or **remove**.
5. Use bulk actions for faster processing.
6. Export the final Excel report.

---

## 📄 License
Internal use.
