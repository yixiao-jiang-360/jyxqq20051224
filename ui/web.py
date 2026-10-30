"""
Web 界面 - 基于 Flask 的轻量网页版
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template_string, request, jsonify, Response
import config
from core.book_analyzer import BookAnalyzer
from core.outline_generator import OutlineGenerator
from core.writer import Writer

app = Flask(__name__)

# 允许上传的扩展名
ALLOWED_EXT = {".txt", ".docx", ".pdf"}

HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>AI 写作助手</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f7; color: #333; }
  .container { max-width: 900px; margin: 0 auto; padding: 20px; }
  h1 { text-align: center; margin: 20px 0 30px; color: #2c3e50; }
  .tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid #3498db; }
  .tab { padding: 10px 20px; background: #ecf0f1; border: none; cursor: pointer; border-radius: 6px 6px 0 0; font-size: 15px; }
  .tab.active { background: #3498db; color: white; }
  .panel { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); display: none; }
  .panel.active { display: block; }
  label { display: block; margin: 12px 0 6px; font-weight: 600; }
  input[type=text], input[type=number], textarea, select {
    width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; font-family: inherit;
  }
  textarea { min-height: 100px; resize: vertical; }
  button { background: #3498db; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 15px; margin-top: 14px; }
  button:hover { background: #2980b9; }
  button:disabled { background: #bdc3c7; cursor: not-allowed; }
  .result { margin-top: 20px; padding: 16px; background: #f8f9fa; border-radius: 8px; white-space: pre-wrap; line-height: 1.8; min-height: 100px; }
  .status { color: #e67e22; font-size: 14px; margin-top: 10px; }
  .book-list { margin-top: 16px; }
  .book-item { padding: 10px; background: #e8f4fd; border-radius: 6px; margin-bottom: 8px; }
</style>
</head>
<body>
<div class="container">
  <h1>📖 AI 网络小说写作助手</h1>
  <div class="tabs">
    <button class="tab active" onclick="switchTab('ingest')">拆书</button>
    <button class="tab" onclick="switchTab('outline')">大纲</button>
    <button class="tab" onclick="switchTab('write')">写作</button>
    <button class="tab" onclick="switchTab('polish')">续写/润色</button>
  </div>

  <!-- 拆书 -->
  <div class="panel active" id="panel-ingest">
    <label>上传文档（txt / docx / pdf）</label>
    <input type="file" id="file" accept=".txt,.docx,.pdf">
    <label>知识库名称</label>
    <input type="text" id="book-name" placeholder="给这本书起个名字">
    <label><input type="checkbox" id="use-emb"> 使用 Embedding 向量检索（需要 API 支持，否则用本地 TF-IDF）</label>
    <button onclick="ingest()">开始拆书</button>
    <div class="status" id="ingest-status"></div>
    <div class="book-list" id="book-list"></div>
  </div>

  <!-- 大纲 -->
  <div class="panel" id="panel-outline">
    <label>新书名称</label>
    <input type="text" id="o-name" placeholder="我的小说">
    <label>参考知识库（可选）</label>
    <select id="o-ref"></select>
    <label>创作要求</label>
    <textarea id="o-req" placeholder="例如：都市玄幻题材，主角是程序员意外获得系统，风格轻松幽默..."></textarea>
    <button onclick="generateOutline()">生成大纲</button>
    <div class="result" id="o-result"></div>
  </div>

  <!-- 写作 -->
  <div class="panel" id="panel-write">
    <label>书名</label>
    <input type="text" id="w-name" placeholder="我的小说">
    <label>绑定知识库（可选）</label>
    <select id="w-ref"></select>
    <label>本章细纲</label>
    <textarea id="w-outline" placeholder="本章要写的内容..."></textarea>
    <label>前文回顾（可选）</label>
    <textarea id="w-context" placeholder="上一章结尾..."></textarea>
    <label>目标字数</label>
    <input type="number" id="w-wc" value="2000">
    <button onclick="writeChapter()">开始写作</button>
    <div class="result" id="w-result"></div>
  </div>

  <!-- 续写/润色 -->
  <div class="panel" id="panel-polish">
    <label>原文</label>
    <textarea id="p-text" style="min-height:200px"></textarea>
    <label>模式</label>
    <select id="p-mode"><option value="continue">续写</option><option value="polish">润色改写</option></select>
    <label>要求</label>
    <input type="text" id="p-req" placeholder="如：续写1000字 / 提升文采 / 改得更紧张">
    <button onclick="polish()">执行</button>
    <div class="result" id="p-result"></div>
  </div>
</div>

<script>
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active', ['ingest','outline','write','polish'][i]===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='outline'||name==='write') loadBooks();
}

async function loadBooks() {
  const r = await fetch('/api/books');
  const books = await r.json();
  ['o-ref','w-ref'].forEach(id=>{
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">不参考</option>' + books.map(b=>`<option value="${b}">${b}</option>`).join('');
  });
  document.getElementById('book-list').innerHTML = books.map(b=>`<div class="book-item">${b}</div>`).join('');
}

async function ingest() {
  const f = document.getElementById('file').files[0];
  if(!f){alert('请选择文件');return;}
  const fd = new FormData();
  fd.append('file', f);
  fd.append('name', document.getElementById('book-name').value || f.name);
  fd.append('use_emb', document.getElementById('use-emb').checked);
  document.getElementById('ingest-status').textContent = '解析中...';
  const r = await fetch('/api/ingest', {method:'POST', body: fd});
  const j = await r.json();
  document.getElementById('ingest-status').textContent = j.message;
  if(j.ok) loadBooks();
}

async function generateOutline() {
  const btn = event.target; btn.disabled = true;
  document.getElementById('o-result').textContent = '生成中...';
  const r = await fetch('/api/outline', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:document.getElementById('o-name').value, ref:document.getElementById('o-ref').value, req:document.getElementById('o-req').value})});
  const reader = r.body.getReader();
  const dec = new TextDecoder(); let out='';
  document.getElementById('o-result').textContent='';
  while(true){
    const {done,value} = await reader.read();
    if(done) break;
    out += dec.decode(value,{stream:true});
    document.getElementById('o-result').textContent = out;
  }
  btn.disabled = false;
}

async function writeChapter() {
  const btn = event.target; btn.disabled = true;
  document.getElementById('w-result').textContent = '写作中...';
  const r = await fetch('/api/write', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:document.getElementById('w-name').value, ref:document.getElementById('w-ref').value,
      outline:document.getElementById('w-outline').value, context:document.getElementById('w-context').value, wc:document.getElementById('w-wc').value})});
  const reader = r.body.getReader();
  const dec = new TextDecoder(); let out='';
  document.getElementById('w-result').textContent='';
  while(true){
    const {done,value} = await reader.read();
    if(done) break;
    out += dec.decode(value,{stream:true});
    document.getElementById('w-result').textContent = out;
  }
  btn.disabled = false;
}

async function polish() {
  const btn = event.target; btn.disabled = true;
  document.getElementById('p-result').textContent = '处理中...';
  const r = await fetch('/api/polish', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text:document.getElementById('p-text').value, mode:document.getElementById('p-mode').value, req:document.getElementById('p-req').value})});
  const reader = r.body.getReader();
  const dec = new TextDecoder(); let out='';
  document.getElementById('p-result').textContent='';
  while(true){
    const {done,value} = await reader.read();
    if(done) break;
    out += dec.decode(value,{stream:true});
    document.getElementById('p-result').textContent = out;
  }
  btn.disabled = false;
}
loadBooks();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/books")
def api_books():
    books = [d.name for d in config.KNOWLEDGE_DIR.iterdir() if d.is_dir()]
    return jsonify(books)


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    f = request.files.get("file")
    name = request.form.get("name", "book")
    use_emb = request.form.get("use_emb") == "true"
    if not f:
        return jsonify({"ok": False, "message": "未上传文件"})
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"ok": False, "message": f"不支持的格式: {ext}"})

    save_path = config.BOOKS_DIR / f.filename
    f.save(str(save_path))

    try:
        analyzer = BookAnalyzer(name)
        n = analyzer.ingest(str(save_path), use_embedding=use_emb)
        return jsonify({"ok": True, "message": f"拆书完成，共 {n} 块"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"失败: {e}"})


@app.route("/api/outline", methods=["POST"])
def api_outline():
    data = request.json
    name = data.get("name", "my_novel")
    ref = data.get("ref", "")
    req = data.get("req", "")

    reference = ""
    if ref:
        analyzer = BookAnalyzer(ref)
        if analyzer.load():
            reference = json.dumps(analyzer.book_profile, ensure_ascii=False)

    gen = OutlineGenerator(name)

    def generate():
        for chunk in gen.generate(req, reference=reference, stream=True):
            yield chunk

    return Response(generate(), mimetype="text/plain")


@app.route("/api/write", methods=["POST"])
def api_write():
    data = request.json
    name = data.get("name", "my_novel")
    ref = data.get("ref", "")
    outline = data.get("outline", "")
    context = data.get("context", "")
    wc = int(data.get("wc", 2000))

    writer = Writer(name)
    if ref:
        writer.bind_knowledge(ref)

    def generate():
        for chunk in writer.write_chapter(outline, context=context, word_count=wc, stream=True):
            yield chunk

    return Response(generate(), mimetype="text/plain")


@app.route("/api/polish", methods=["POST"])
def api_polish():
    data = request.json
    text = data.get("text", "")
    mode = data.get("mode", "continue")
    req = data.get("req", "")

    writer = Writer()
    if mode == "polish":
        gen = writer.polish(text, instructions=req, stream=True)
    else:
        gen = writer.continue_writing(text, requirements=req, stream=True)

    def generate():
        for chunk in gen:
            yield chunk

    return Response(generate(), mimetype="text/plain")


def run_web():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    print("🌐 Web 界面启动: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    run_web()
