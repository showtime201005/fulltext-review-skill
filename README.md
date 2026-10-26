# Fulltext Literature Review

閱讀使用者提供的學術論文 Markdown 全文與圖片，產生逐篇報告、獨立查核紀錄與主題式文獻綜述。輸出使用使用者指定的語言。

## 開始使用

完整安裝與交付方式請看 [交付說明](交付說明.md)；工作流程定義於 [SKILL.md](.agents/skills/fulltext-literature-review/SKILL.md)。

使用 LangChain Deep Agents SDK 的串接方式與試跑範例，請看 [Deep Agents 串接指南](DEEPAGENTS_GUIDE.md)。

- 需要能讀寫檔案、查看圖片、執行 Python 與建立子代理的 AI 工具。
- 需要 Python 3.10 以上，腳本只使用標準函式庫。
- 請自行準備論文 Markdown 與圖片；本 skill 不負責論文取得或 PDF 轉換。

## 專案內容

| 路徑 | 用途 |
|---|---|
| `.agents/skills/fulltext-literature-review/` | 可交付的完整 skill、規則與腳本 |
| `tests/` | 自動測試、測試情境與固定測試資料 |
| `SKILL_GUIDE.html` | Skill 說明頁 |
| `VALIDATION.md`、`*_PLAN.md`、`IMPLEMENTATION_SPEC.md` | 驗證紀錄與開發文件 |

本機論文資料夾、`runs/` 產出、`tests/results/` 歷史測試產出及 Python 快取由 `.gitignore` 排除，不會隨 Git 版本交付。

## 執行測試

在專案根目錄執行：

```text
python -X utf8 -m unittest discover -s tests -v
```

`-X utf8` 可避免部分測試受到 Windows 預設文字編碼影響。若系統找不到 `python`，請改用實際安裝的 Python 執行檔路徑。
