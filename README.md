![alt text](https://github.com/EYAIChallenge/Overview/blob/main/Banner-EY-1280x640.jpg "EY AI Challenge")

<h1 align="center"> <img src="https://github.com/EYAIChallenge/Overview/blob/main/EY_Logo_Beam_RGB_White_Yellow.png" width="40" alt="Logo"/> AI Challenge 2026 | Law Agent Challenge </h1>

---

## 📋 Description

In Portugal, as in many countries, legal documents such as **laws, codes**, and **regulations** often reference each other, forming a complex web of interconnected texts. In this challenge, you will focus on two significant pillars of Portuguese law:

- **Código do Trabalho (Labour Code)**
- **Código Civil (Civil Code)**

These legal documents often reference each other or other laws, creating **"clusters"** of interrelated legislation. Your goal is to uncover, visualize, and analyze these relationships strategically.

### **Objective**  
Design a solution that identifies and maps the connections between legal documents based on how they cite or refer to one another. For example, if **Lei nº 1** refers to **Lei nº 33**, this implies a legal or conceptual dependency that can be mapped.

You'll use a combination of text processing, information extraction, and relationship mapping to construct a meaningful representation of these links. Your final solution should enable exploration, analysis, or visual storytelling of how Portuguese laws interconnect, providing strategic insights that transform raw legal text into actionable intelligence.

---

## 📂 Data

The provided dataset consists of 20 PDF documents, each containing either a Decree-Law (Decreto de Lei) or a Law Consolidation (Artigo de Lei). These documents are divided into the two major pillars of Portuguese law mentioned earlier:

- **10 documents related to the Labour Code** (ranging from 1 to 102 pages).
- **10 documents related to the Civil Code** (ranging from 3 to 42 pages).

Each PDF contains the full legal text of a specific law or consolidation, and may include references, citations, or mentions to other legal documents within the dataset. 

---

## 💡 What You Can Do (But Not Limited To)

- **Extract and map references** between legal documents (e.g., "Lei n.º X/2001", "Artigo 45.º").
- **Create graph-based visualizations** to illustrate clusters or citation networks.
- **Identify influential laws**, central articles, or overlapping content.
- **Use language models** (e.g., embeddings or heuristics) to detect **implicit references**.
- **Cluster or color-code** laws based on origin (Código do Trabalho vs Código Civil).
- **Suggest potential inconsistencies** or areas of interest for legal professionals or policymakers.
- Provide a UI, query interface, or dashboard to explore the connections (optional but encouraged).

---

## 🎯 Deliverables

- ✅ A **working prototype** or concept that maps interconnections between the laws.
- ✅ An **organized and well-documented code** that is reproducible.
- ✅ A **short presentation** to pitch your solution as if to potential clients.
- ✅ (Optional) It’s a major plus if your presentation includes a brief live demo to showcase how the solution works in practice, you can even present over it.
- *(Optional)* **Visualizations**, interactive tools, or insights that provide additional analysis.

<h2 align="center"> ⚠️ **Important Submission Requirement** ⚠️ </h2>
<h3> ✅ Before the 14h00 deadline</h3>

Submit a zip folder with:
- The **Google Colab notebook** (with all cells run & outputs shown).
- Screenshots of all **external tools/visualizations** used.

Submit via email to: [eyaichallenge@pt.ey.com](mailto:eyaichallenge@pt.ey.com)

Subject: `Law Document Mapping – GroupName`

Include group member names in the email.


---

## 👩‍💼 Consulting Mindset Expectations

We are looking for teams who think strategically:

- **Problem Framers**: Reframe how the problem is understood, not just solved.
- **Insight Generators**: Convert data into **meaningful**, actionable intelligence.
- **Innovative Thinkers**: Challenge conventional approaches to legal research and knowledge management.
- **Sell the Solution**: Don't just explain what you built—**present it as a valuable solution** for the client, highlighting **business impact** and proposing clear next steps.

---

## 🧠 Tips for Competitors

- **Choose Your Language Model (LLM) Wisely**: Consider **Gemini** (fast but with context limits) vs **LLaMA** (slower, but handles more context). Each have trade-offs. Choose based on your solution's priorities and feel free to explore other options.
- **Explore the Data**: Understand the structure of **Portuguese laws** (e.g., article numbers, cross-law citations).
- **Design the Pipeline**: How do you go from raw **legal text** (PDFs, HTML, etc.) to structured, explorable knowledge?
- **Be Open**: Focus on citations, text similarity, semantic relationships, keyword overlap, or anything else revealing meaningful links.
- **Think Like a User**: Consider insights that law students, researchers, or clients would want from your system.
- **Make It Scalable**: Your solution should easily handle dozens or hundreds of legal documents.
- **Be Creative**: Don’t shy away from unconventional approaches in **AI**, **NLP**, and **data science**.
- **Tell the Story**: Present your work in a compelling way, showing clear **business impact**.

---

## 🛠 Tech & Tools – You Have Full Freedom

It is mandatory to develop the solution in **Google Colab using Python**.
Other than that, you are completely free to choose your own:

- **Libraries and packages**: Use any tool you need (e.g., Pandas, Scikit-learn, LangChain, etc.)
- **Visualization tools**: Python-based tools (Matplotlib, Seaborn), Power BI, Tableau, etc.
- **AI assistants**: Feel free to consult ChatGPT, GitHub Copilot, Gemini, or any other. 

---

## ⏱ Time Management & Rules

- ⏳ You have **4 hours total** to complete your challenge  
  🔒 **No extensions** will be allowed

- 🗣 After the working session, deliver a **5-minute presentation**  
  🎯 Simulate a **client-facing consulting pitch**

- 👥 Each group is allowed:
  - `1` **technical support** session (up to 5 minutes)
  - `1` **business-related support** session (up to 5 minutes)

> 🧠 Assistants will guide your thinking, not provide direct solutions

---

## 🧑‍💼 Strategy & Workflow Tips

- **Assign Roles Early**: e.g., a data person, a business analyst, and a presenter. 
- **Work in Parallel**: Don’t wait on each other. Split tasks and collaborate strategically.
- **Prepare for the Presentation**: Start preparing early; don’t leave it to the last 10 minutes.
- **Be Realistic**: It’s better to deliver a focused, clear, and well-explained solution than a rushed or overly complex one.

💡 **Pro Tip**: You are not being judged only on technical accuracy, but also on how you think, structure, work as a team and communicate your approach.

---

## 💭 Final Thought

This challenge is as much about strategic thinking and business insight as it is about technical implementation. You are encouraged to explore the legal data in your own way and shape a solution that reflects your team's unique vision. Remember that you're not just building a tool – you're creating a strategic solution that could transform how legal professionals navigate complex legal networks.

---

### 🏁 Brought to you by **EY AI Challenge**
