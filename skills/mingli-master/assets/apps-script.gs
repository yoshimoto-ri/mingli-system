/**
 * 命理系統 - Google Sheets 寫入端點
 * 部署: script.google.com → 新專案 → 貼上本檔 → 部署 → 網頁應用程式
 *   執行身分: 我 / 具有存取權的使用者: 任何人 → 複製網址
 * 自動在「我的雲端硬碟/命理系統」建立試算表「命理系統紀錄」並逐筆附加。
 */
const FOLDER_NAME = '命理系統';
const SHEET_NAME = '命理系統紀錄';
const HEADERS = ['時間戳', '姓名', '性別', '出生時間', '出生地', '問事類別',
                 '紫微摘要', '占星摘要', '易經摘要', '姓名學摘要', '擇日摘要', '結論'];

function getFolder_() {
  const folders = DriveApp.getFoldersByName(FOLDER_NAME);
  return folders.hasNext() ? folders.next() : DriveApp.createFolder(FOLDER_NAME);
}

function getSheet_() {
  const folder = getFolder_();
  const files = folder.getFilesByName(SHEET_NAME);
  let ss;
  if (files.hasNext()) {
    ss = SpreadsheetApp.open(files.next());
  } else {
    ss = SpreadsheetApp.create(SHEET_NAME);
    DriveApp.getFileById(ss.getId()).moveTo(folder);
    ss.getActiveSheet().appendRow(HEADERS);
  }
  return ss.getActiveSheet();
}

function uploadPdf_(filename, base64Data) {
  const folder = getFolder_();
  const bytes = Utilities.base64Decode(base64Data);
  const blob = Utilities.newBlob(bytes, 'application/pdf', filename);
  const file = folder.createFile(blob);
  return { ok: true, fileId: file.getId(), url: file.getUrl(), filename: filename };
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const d = JSON.parse(e.postData.contents);

    if (d.action === 'upload_pdf') {
      const result = uploadPdf_(d.filename, d.data);
      return ContentService.createTextOutput(JSON.stringify(result))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const sheet = getSheet_();
    sheet.appendRow([
      new Date(), d['姓名'] || '', d['性別'] || '', d['出生時間'] || '', d['出生地'] || '',
      d['問事類別'] || '', d['紫微摘要'] || '', d['占星摘要'] || '', d['易經摘要'] || '',
      d['姓名學摘要'] || '', d['擇日摘要'] || '', d['結論'] || ''
    ]);
    return ContentService.createTextOutput(JSON.stringify({ ok: true, row: sheet.getLastRow() }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return ContentService.createTextOutput(JSON.stringify({ ok: true, msg: '命理系統端點運作中' }))
    .setMimeType(ContentService.MimeType.JSON);
}
