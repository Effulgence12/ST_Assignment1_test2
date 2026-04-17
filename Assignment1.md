# Assignment 1

## 1\. Requirements

The assignment requires students to design and implement (or enhance) a testing technique using AI methods (e.g., LLMs). The students can either choose static testing, black-box dynamic testing or white-box dynamic testing techniques.

**Note:**

- **Static code analysis:** The page shows the list of tools for static code analysis.
- **Black-box testing techniques:** include Equivalence Partitioning (EP), Boundary Value Analysis (BVA), Testing Combinations of Inputs, State Transition Testing Model Generator, Decision Table Testing.
- **White-box testing:** can measure the statement coverage, branch coverage, condition coverage, path coverage, d-u coverage, etc.

Now the assignment requires students to implement it as a tool where it can take either two forms of input:

1.  The requirements of a system.
2.  The testing codebase.

The tool is expected to analyze either (1) the requirements of a system; (2) the testing codebase (or a partial module) to create test cases.

## 2\. Submission Artifact

1.  **Input:** requirement/project code base
2.  **Tool artifact:** prompts used, model used, model-generated code
3.  **Generated output:**
    - Reported alarms (for static analysis)
    - Test cases (for black- and white-box analysis)
4.  **Experimental Analysis:** (Accuracy, Coverage, Generalizability, etc.)
5.  **Project report:**  
    a. Comparison to traditional non-AI-based technique, pros and cons.  
    b. Analytical report: How you encounter limitations of AI and how you improve the tool while practicing?  
    c. Summary.

## 3\. Assessment Criteria

- Understanding of concepts: 10%
- Coherence of design and implementation: 20%
- Coverage and effectiveness/usefulness: 40%
- In-depth analysis (generalizability demonstration, reasoning, etc.): 20%
- Presentation: 10%

## 4\. Presentation & Submission

### Presentation

- Each group has 15 minutes to complete the project presentation in English.
- A Q&A session follows. Reviewers will ask questions based on documents and software testing fundamentals.

### Submission

- **Deadline:** Week 8 (April 20th), Monday, before 17:00 pm.
- **Materials:** Submission Artifact (PDF), Final Presentation PPT (PDF), and test scripts (compressed file).
- **Email:** Submit to TA with team ID, full names, and student IDs.

## Example Submission Ex1:

**Title: LLM-based Dynamic Black-box Testing for Multi-Item Smart Vending Machine**

### 1\. Input:

**System Overview:** The system under test is a smart vending machine. Internal logic is not visible (Black-box).

**Functional Requirements:**

- **R1. Item Selection:** Drinks ($1.50, $3.00); Snacks ($2.00, $4.50); Hot food ($5.00, $10.00).
- **R2. Payment Methods:** Coins ($0.10, $0.25, $0.50, $1.00); Banknotes ($5.00, $10.00).
- **R3. Payment Constraints:** Total inserted  price. Change return limit: $5.00.
- **R4. Inventory Constraints:** Items may become out of stock.

### 2\. Tool Artifact:

- **LLM Used:** GPT-4o
- **Prompt Used:**

You are a software testing assistant. Given the following system overview and requirement, identify:

- 1.  Input variables 2) Equivalence partitions (valid and invalid) 3) Boundary values 4) Concrete test cases  
        Requirement: {requirement_text}

### 3\. Generated Output:

**Equivalence Partitioning:**

| **ID** | **Description** | **Outcome** |
| --- | --- | --- |
| EP1 | Inserted amount < item price | valid |
| --- | --- | --- |
| EP2 | Inserted amount > item price | invalid |
| --- | --- | --- |

**Boundary Value Analysis:**

| **Boundary** | **Values** |
| --- | --- |
| Item price | $1.4, $1.5, $1.6 |
| --- | --- |
| Payment Total | $0, $1.4, $15.1 |
| --- | --- |

**Sample Test Cases:**

| **Test Case** | **Scenario** | **Expected Result** |
| --- | --- | --- |
| TC1 | Snack $3.00, paid $8.50 | Reject (change > $5) |
| --- | --- | --- |
| TC2 | Snack $3.00, paid $3.50 | Success, return change $0.50 |
| --- | --- | --- |

## Example Submission Ex2:

**Title: LLM-based Static Analysis**

### 1\. Input:

**System Overview:** Axios is a promise-based network library. Analysis on Axios v1.3.4 adapted for OpenHarmony.

### 2\. Tool Artifact:

**Example Prompt:**

You are a static code analyzer. Analyze the following {language} code and detect potential issues: 1. Syntax errors, 2. Security vulnerabilities, 3. Deprecated API, 4. Runtime errors, 5. Code quality. Return results in JSON.

### 3\. Generated Output:

{  
"issues": \[  
{  
"line": 4,  
"type": "Resource Management",  
"description": "File opened using 'open' but not managed with a context manager.",  
"severity": "medium",  
"recommendation": "Use 'with open(filename, 'r') as f:'",  
"category": "Code Quality"  
}  
\]  
}  

**Proof of Concept (Test Case):**

import os  
<br/>def test_resource_management_leak():  
filename = "testfile.txt"  
with open(filename, "w") as f:  
f.write("Hello World!")  
<br/>def read_file_bad(filename):  
f = open(filename, 'r')  
data = f.read()  
raise Exception("Simulated error")  
f.close()  
return data  
<br/>try:  
read_file_bad(filename)  
except Exception as e:  
print(f"Caught exception: {e}")  
<br/>try:  
os.remove(filename)  
print("File successfully deleted")  
except PermissionError:  
print("File deletion failed: resource leak")  

## Example Submission Ex3:

**Title: LLM-based White-box Testing**

### 1\. Input:

**Code Snippet (Axios deleteFile):**

try {  
const deleteFile = (cacheDir:string, options: request.UploadConfig): void => {  
const axios_temp = 'axios_temp';  
let path_temp = \`${cacheDir}/${axios_temp}/\`;  
if (options) {  
options && options.files.forEach(item => {  
item.uri && fs.unlink(item.uri.replace('internal://cache/${axios_temp}/', path_temp));  
});  
let filenames = fs.listFileSync(path_temp);  
let now = Date.now();  
for (let i = 0; i < filenames.length; i++) {  
let path = path_temp + filenames\[i\];  
let stat = fs.statSync(path);  
if (now - stat.atime >= 12 \* 60 \* 60 \* 1000) {  
fs.unlink(path);  
}  
}  
}  
}  
} catch (err) {  
hilog.error(DOMAIN, TAG, \`delete file failed: ${err.message}\`);  
}  

### 2\. Tool Artifact:

**Prompt:**

You are an expert software tester. Analyze the following function and generate test cases for **full statement coverage**. Output in structured JSON.

### 3\. Generated Output:

{  
"function": "deleteFile",  
"test_cases": \[  
{  
"id": "TestCase1",  
"description": "Delete Specified Files",  
"input": {  
"cacheDir": "/tmp/cache",  
"options": {  
"files": \[{ "uri": "internal://cache/axios_temp/file1.txt" }\]  
}  
},  
"covered_statements": \[47, 48, 49, 50, 51\]  
}  
\]  
}