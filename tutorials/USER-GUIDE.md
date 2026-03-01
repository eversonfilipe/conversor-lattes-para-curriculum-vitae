# Complete User Guide: Lattes to PDF Converter

Welcome! This guide was specifically designed for users with **no programming experience**. If you are a researcher, professor, or student who needs to transform your Brazilian Lattes CV into a clean, professional, and internationally formatted PDF, you are in the right place.

Here, we will explain the process step-by-step in a simple and visual way.

---

## Table of Contents
1. [What You Will Need (Prerequisites)](#1-what-you-will-need)
2. [Step 1: Downloading your Lattes in XML](#step-1-downloading-your-lattes-in-xml)
3. [Step 2: Preparing the Converter](#step-2-preparing-the-converter)
4. [Step 3: Generating your PDF](#step-3-generating-your-pdf)
5. [Step 4: Editing Information (Optional)](#step-4-editing-information)
6. [Frequently Asked Questions (FAQ)](#frequently-asked-questions)
7. [Video Tutorials](#video-tutorials)

---

## 1. What You Will Need
To ensure the PDF fonts and Portuguese accent marks render perfectly, this program runs locally on your own computer.
* **Operating System:** We highly recommend using **Windows** (it natively includes the *Times New Roman* fonts required for the document).
* **Anaconda Navigator:** This is a free software package that includes everything Python and Jupyter Notebook need to run, without requiring you to type any complex code. [Download Anaconda here](https://www.anaconda.com/download).

---

## Step 2: Downloading your Lattes in XML
You must extract your official data directly from the CNPq platform.

1. Access the [Lattes Platform](https://lattes.cnpq.br/) and log into your CV.
2. In the top right menu, click the **Export CV** (Exportar currículo) button.
3. Select the option to export in **XML** format.
4. The website will download a compressed file (e.g., `CV_1234567890.zip`). **Do not extract this file!** *[Insert image of the Lattes platform export XML option here]*

---

## Step 3: Preparing the Converter
Now let's load your CV into the tool.

1. Download this project by clicking the green **"Code"** button at the top of this GitHub page, then select **"Download ZIP"**.
2. Extract this project folder on your computer (your Desktop is fine).
3. Take the `.zip` file you downloaded from Lattes in Step 1 and paste it **inside the converter folder** you just extracted.

**Attention:** The converter folder must contain the `lattes_para_pdf.ipynb` file and your `CV_1234567890.zip` file side by side.

*[Insert image of a computer folder showing the Jupyter notebook file and the downloaded Lattes ZIP file together]*

---

## Step 4: Generating your PDF
Now it's time to make the magic happen.

1. Open **Anaconda Navigator** on your computer.
2. Look for the **Jupyter Notebook** application and click **Launch**.
3. A new tab will open in your web browser showing your computer's folders. Navigate to the converter folder.
4. Click on the `lattes_para_pdf.ipynb` file to open it.
5. With the file open, go to the top menu and click **Cell > Run All**. 
6. Scroll to the bottom of the page. The system will automatically process your data and, in a few seconds, it will create the `_cv.pdf` file in the same folder!

---

## Step 5: Editing Information (Optional)
If you want to delete, translate, or add any entries before generating the final PDF:

1. At the very bottom of the Jupyter Notebook (Block 5), an **Interactive CV Editor** will appear.
2. Navigate through the tabs (Personal Data, Experience, etc.).
3. Modify the text directly inside the input boxes.
4. When finished, click the green **"Save & Regenerate PDF"** button. Your PDF will be updated instantly!

*[Insert image of the interactive CV editor interface showing the Save and Regenerate PDF button]*

---

## Frequently Asked Questions (FAQ)

**Error: "ZIP not found by exact name"**
* **What it means:** The converter could not find your Lattes CV.
* **How to fix it:** Ensure that the `.zip` file downloaded from Lattes is located in the exact same folder as the `lattes_para_pdf.ipynb` file.

**Error: "WARNING: Windows TTF not found"**
* **What it means:** The converter could not locate the Times New Roman font on your computer.
* **How to fix it:** This usually happens if you are using macOS or Linux. The PDF will still be generated, but accented characters might display incorrectly in bold text. We recommend using Windows.

---

## 🎬 Video Tutorials

We have prepared short videos (under 2 minutes) for each step:

* 🎥 **[Tutorial 1] How to properly export your Lattes XML.** *(Insert video link)*
* 🎥 **[Tutorial 2] How to install Anaconda and open the Converter.** *(Insert video link)*
* 🎥 **[Tutorial 3] How to run the code and generate your first PDF.** *(Insert video link)*
* 🎥 **[Tutorial 4] How to use the Interactive Editor to translate or alter data.** *(Insert video link)*
