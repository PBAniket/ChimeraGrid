# 🌟 TabulaX

**TabulaX** is a web-based AI tool that automates multi-class table transformations using large language models (LLMs). With a user-friendly interface and powerful Gemini 1.5 Flash integration, it generates clean Python functions to transform your tabular data with just a few examples.

---


## 📸 Screenshots

### 🔹 Input Table
![Input Table](Screenshot%202025-07-14%20112516.png)


### 🔹 Generated Output
![Output Function](Screenshot%202025-07-14%20112551.png)

---

## 🚀 Features

- 🔠 **String Transformations** – Modify case, extract substrings, replace values, etc.
- 🔢 **Numerical Transformations** – Convert units, apply scaling, curve fitting, etc.
- 📅 **Algorithmic Transformations** – Date formatting, parsing, and re-encoding
- 🌐 **General Knowledge** – Entity mapping using LLM-powered inference
- 🧾 **Human-readable Output** – Transparent, editable Python code is generated
- 💡 **Interactive UI** – Clean and responsive UI using Tailwind CSS

---

## 🛠 Tech Stack

| Layer        | Technology                         |
|--------------|------------------------------------|
| Frontend     | HTML, CSS, JavaScript, Tailwind CSS|
| Backend      | Python, Flask                      |
| LLM Engine   | Gemini 1.5 Flash (via `google-generativeai`) |
| Data Tools   | Pandas, JSON                       |

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/PBAniket/ChimeraGrid.git
cd ChimeraGrid
pip install -r requirements.txt
python app.py
