![alt text](https://github.com/EYAIChallenge/Overview/blob/main/Banner-EY-1280x640.jpg "EY AI Challenge")

<h1 align="center"> <img src="https://github.com/EYAIChallenge/Overview/blob/main/EY_Logo_Beam_RGB_White_Yellow.png" width="40" alt="Logo"/> AI Challenge 2026 | Law Agent Challenge </h1>

---

## 📋 Description

In Portugal, as in many countries, legal documents such as **laws, codes**, and **regulations** often reference each other, forming a complex web of interconnected texts. In this challenge, you will focus on two significant pillars of Portuguese law:

- **Código do Trabalho (Labour Code)**
- **Código Civil (Civil Code)**

These legal documents often reference each other or other laws, creating **"clusters"** of interrelated legislation. Your goal is to uncover, visualize, and analyze these relationships strategically.

🎯 **Objective:**    
Design a solution that identifies, extracts, and maps the relationships between legal documents based on how they reference or cite one another. For example, if Lei nº 1 refers to Lei nº 33, this establishes a legal or conceptual dependency that can be represented as part of a broader network.

Leverage techniques such as text processing, information extraction, and graph-based modeling (e.g., GraphRAG) to build a structured representation of these connections.

Your final solution should include a virtual assistant capable of querying this network using natural language. The system should enable users to explore, analyze, and understand how Portuguese laws are interconnected -transforming complex legal text into accessible, actionable insights through graph exploration, analysis, or visual storytelling.

---

## 📂 Data

You should consider as your dataset the PDFs documents from Diário da República, containing either information about Decree-Law (Decreto de Lei) or Law Consolidation (Artigo de Lei). These 

- **Data source** - https://diariodarepublica.pt/dr/legislacao-por-tema

Each PDF contains the full legal text of a specific law or consolidation, and may include references, citations, or mentions to other legal documents within the dataset. 

---

## 💡 What You Can Do (But Not Limited To)

- **Extract and map references** between legal documents (e.g., "Lei n.º X/2001", "Artigo 45.º").
- **Create graph-based visualizations** to illustrate clusters or citation networks.
- **Identify influential laws**, central articles, or overlapping content.
- **Use language models** (e.g., embeddings or heuristics) to detect **implicit references**.
- **Cluster or color-code** laws based on origin (Código do Trabalho vs Código Civil).
- **Suggest potential inconsistencies** or areas of interest for legal professionals or policymakers.
- Provide a UI, query interface, or dashboard to explore the connections.

---

## 📦 Deliverables

- ✅ A working prototype of your strategic conversational assistant
- ✅ Organized and well-documented code, that can be reproducible
- ✅ A strategic presentation pitching your solution to the judging panel as if they were the client's executive stakeholders
- ✅ A technical presentation pitching your solution to the judging panel as if they were the client's IT stakeholders
- ✅ A frontend for the solution is mandatory for the live demo of the strategic presentation

🔹 **Optional Enhancements**:  
- Performance analysis vs traditional knowledge access methods

<h2 align="center"> ⚠️ **Important Submission Requirement** ⚠️ </h2>
<h3> ✅ Before the 14h00 deadline</h3>

Submit you solution to your specific branch:
- Repository with the code of the solution developed
  - The solution must be ready to run
- A README file with the context of the solution and how to run it


---

## 👩‍💼 Consulting Mindset Expectations

We are looking for teams who think strategically:

- **Problem Framers**: Reframe how the problem is understood, not just solved.
- **Insight Generators**: Convert data into **meaningful**, actionable intelligence.
- **Innovative Thinkers**: Challenge conventional approaches to legal research and knowledge management.
- **Sell the Solution**: Don't just explain what you built—**present it as a valuable solution** for the client, highlighting **business impact** and proposing clear next steps.

---

## 🧠 Tips for Competitors

- **Choose Your Language Model (LLM) Wisely**
- **Explore the Data**: Understand the structure of **Portuguese laws** (e.g., article numbers, cross-law citations).
- **Design the Pipeline**: How do you go from raw **legal text** (PDFs, HTML, etc.) to structured, explorable knowledge?
- **Be Open**: Focus on citations, text similarity, semantic relationships, keyword overlap, or anything else revealing meaningful links.
- **Think Like a User**: Consider insights that law students, researchers, or clients would want from your system.
- **Make It Scalable**: Your solution should easily handle dozens or hundreds of legal documents.
- **Be Creative**: Don’t shy away from unconventional approaches in **AI**, **NLP**, and **data science**.
- **Tell the Story**: Present your work in a compelling way, showing clear **business impact**.

---

## 🛠️ Tech & Tools

- **Mandatory:**  
  - Solution must be developed mainly using Python  
  - You'll publish the solution into a specific branch of the challenge's repository

- **Free to Choose:**  
  - Libraries/Packages
  - Visualization
  - Frontend solution
  - AI Assistants

---

## ⏱️ Time Management & Rules

- Total Time: **4 hours** – No extensions  
- Final Presentations: **5 minutes each** – Simulate a client-facing pitch
  - You must divide the team for the strategic and technical presentations
- Support:
  - 🧑‍💻 1 technical session (max 5 minutes)  
  - 💼 1 business session (max 5 minutes)  
  - **Note:** Assistants guide only — no direct solutions

---

## 📋 Strategy & Workflow Tips

1. **Assign Roles Early** — e.g., data analyst, business strategist, presenter  
2. **Work in Parallel** — Divide and conquer  
3. **Start the Presentation Early** — Don’t wait until the last 10 minutes  
4. **Be Realistic** — Focused and clear beats complex and incomplete  

💡 **Pro Tip:**  
Judging includes **teamwork**, **structure**, and **communication**, not just technical quality

---

## 💭 Final Thought

This challenge is as much about strategic thinking and business insight as it is about technical implementation. You are encouraged to explore the legal data in your own way and shape a solution that reflects your team's unique vision. Remember that you're not just building a tool – you're creating a strategic solution that could transform how legal professionals navigate complex legal networks.

---

### 🏁 Brought to you by **EY AI Challenge**
