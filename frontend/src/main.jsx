import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Upload, Sparkles, FileText, Linkedin, Presentation, Megaphone,
  BarChart3, Video, Image as ImageIcon, X, Download, Copy, Check,
  Settings2, Zap, ShieldCheck
} from "lucide-react";
import "./styles.css";

const API = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").replace(/\/$/, "");

const outputOptions = [
  ["linkedin", "LinkedIn Post", Linkedin],
  ["x", "X / Twitter Thread", Zap],
  ["advisory", "Advisory", Megaphone],
  ["summary", "Executive Summary", FileText],
  ["presentation", "Presentation", Presentation],
  ["infographic", "Infographic", BarChart3],
  ["video", "Video Package", Video],
];

function App() {
  const [file, setFile] = useState(null);
  const [source, setSource] = useState("");
  const [outputs, setOutputs] = useState(["linkedin", "summary", "presentation"]);
  const [settings, setSettings] = useState({
    audience: "General",
    tone: "Professional",
    language: "English",
    detail: "Medium",
    objective: "Inform",
    style: "Clear and concise"
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  const selectedNames = useMemo(
    () => outputs.map(k => outputOptions.find(x => x[0] === k)?.[1]).filter(Boolean),
    [outputs]
  );

  const toggle = (key) =>
    setOutputs(prev => prev.includes(key) ? prev.filter(x => x !== key) : [...prev, key]);

  const update = (key, value) => setSettings(s => ({ ...s, [key]: value }));

  const generate = async () => {
    if (!file && !source.trim()) {
      setError("Add source text or upload a document first.");
      return;
    }
    if (!outputs.length) {
      setError("Select at least one output.");
      return;
    }

    setError("");
    setLoading(true);
    setResult(null);

    try {
      let response;
      if (file) {
        const form = new FormData();
        form.append("file", file);
        form.append("outputs", JSON.stringify(outputs));
        Object.entries(settings).forEach(([k, v]) => form.append(k, v));
        response = await fetch(`${API}/transform-upload`, { method: "POST", body: form });
      } else {
        response = await fetch(`${API}/transform`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ source_text: source, outputs, ...settings })
        });
      }

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Generation failed.");
      setResult(data);
    } catch (e) {
      setError(e.message || "Could not connect to the backend. Start FastAPI on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const copyText = async (key, value) => {
    const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(""), 1200);
  };

  const exportPptx = async () => {
    if (!result?.outputs?.presentation) return;
    const response = await fetch(`${API}/export/pptx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: result.outputs.presentation.title, outputs: result.outputs })
    });
    if (!response.ok) {
      setError("PPTX export failed.");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "contentforge-presentation.pptx";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brandMark"><Sparkles size={19}/></div>
          <div>
            <strong>ContentForge AI</strong>
            <span>Content Transformation Engine</span>
          </div>
        </div>
        <div className="status"><span className="dot"/> AI workspace</div>
      </header>

      <main className="shell">
        <section className="hero">
          <div>
            <div className="eyebrow">ONE SOURCE → MANY ARTEFACTS</div>
            <h1>Transform information into communication.</h1>
            <p>Upload a report, article, document or paste text. Choose the deliverables and let one shared source context power every output.</p>
          </div>
          <div className="heroCard">
            <ShieldCheck size={22}/>
            <div><b>Source-grounded workflow</b><span>Same source → consistent outputs</span></div>
          </div>
        </section>

        <div className="grid">
          <section className="panel">
            <div className="panelTitle"><span>01</span><div><h2>Source content</h2><p>Upload a file or paste high-quality English text.</p></div></div>

            <label className="dropzone">
              <input type="file" accept=".txt,.md,.pdf,.docx,.png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0] || null)} />
              <Upload size={28}/>
              <b>{file ? file.name : "Drop a document or click to upload"}</b>
              <span>TXT · PDF · DOCX · PNG · JPG · WEBP</span>
            </label>

            {file && <div className="fileChip"><FileText size={16}/>{file.name}<button onClick={() => setFile(null)}><X size={15}/></button></div>}

            <div className="or"><span>OR</span></div>
            <textarea
              value={source}
              onChange={e => setSource(e.target.value)}
              placeholder="Paste source content here..."
            />
          </section>

          <section className="panel">
            <div className="panelTitle"><span>02</span><div><h2>Deliverables</h2><p>Select one or more outputs from the same source.</p></div></div>
            <div className="outputGrid">
              {outputOptions.map(([key, name, Icon]) => (
                <button key={key} className={`outputCard ${outputs.includes(key) ? "selected" : ""}`} onClick={() => toggle(key)}>
                  <Icon size={20}/>
                  <span>{name}</span>
                  {outputs.includes(key) && <Check size={15}/>}
                </button>
              ))}
            </div>

            <div className="panelTitle small"><span>03</span><div><h2>Generation controls</h2></div><Settings2 size={18}/></div>
            <div className="controls">
              {[
                ["audience","Audience",["General","Executives","Technical Team","Public","Students"]],
                ["tone","Tone",["Professional","Formal","Conversational","Urgent","Educational"]],
                ["language","Language",["English","Hindi","Hinglish"]],
                ["detail","Detail",["Concise","Medium","Detailed"]],
                ["objective","Objective",["Inform","Awareness","Persuade","Brief","Educate"]],
                ["style","Style",["Clear and concise","Executive","Social-first","Technical"]]
              ].map(([key,label,options]) => (
                <label key={key}><span>{label}</span><select value={settings[key]} onChange={e => update(key,e.target.value)}>{options.map(o=><option key={o}>{o}</option>)}</select></label>
              ))}
            </div>

            <button className="generate" disabled={loading} onClick={generate}>
              {loading ? <><span className="spinner"/> Generating...</> : <><Sparkles size={18}/> Generate {outputs.length} deliverable{outputs.length !== 1 ? "s" : ""}</>}
            </button>
            {error && <div className="error">{error}</div>}
          </section>
        </div>

        {result && (
          <section className="results">
            <div className="resultHeader">
              <div><div className="eyebrow">GENERATED OUTPUTS</div><h2>Communication workspace</h2></div>
              <div className={`mode ${result.mode?.includes("fallback") ? "warningMode" : ""}`}>Engine: {result.mode}</div>
            </div>
            {result.source_intelligence && (
              <div className="sourceIntel">
                <div><b>Source Intelligence</b><span>{result.source_intelligence.content_type || "source"}</span></div>
                <strong>{result.source_intelligence.title || "Source analyzed"}</strong>
                <p>{result.source_intelligence.summary}</p>
                {result.source_intelligence.key_facts?.length > 0 && <ul>{result.source_intelligence.key_facts.slice(0,5).map((x,i)=><li key={i}>{x}</li>)}</ul>}
              </div>
            )}

            <div className="resultGrid">
              {Object.entries(result.outputs).filter(([k]) => k !== "_warning").map(([key, value]) => (
                <article className="resultCard" key={key}>
                  <div className="resultCardHeader">
                    <div><span className="resultTag">{outputOptions.find(x=>x[0]===key)?.[1] || key}</span><h3>{value.title || value.headline || key}</h3></div>
                    <button className="iconBtn" onClick={() => copyText(key, value)} title="Copy">
                      {copied === key ? <Check size={16}/> : <Copy size={16}/>}
                    </button>
                  </div>
                  <ResultBody type={key} data={value}/>
                </article>
              ))}
            </div>

            {result.outputs.presentation && (
              <button className="export" onClick={exportPptx}><Download size={17}/> Export Presentation as PPTX</button>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function ResultBody({type,data}) {
  if (type === "linkedin") {
    return <div className="rich">
      {data.hook && <p><b>Hook:</b> {data.hook}</p>}
      <p>{data.content}</p>
      {data.hashtags?.length > 0 && <p><b>{data.hashtags.join(" ")}</b></p>}
    </div>;
  }
  if (type === "summary") {
    return <div className="rich">
      <p>{data.executive_summary || data.summary}</p>
      {data.key_points && <ul>{data.key_points.map((x,i)=><li key={i}>{x}</li>)}</ul>}
      {data.implications && <p><b>Implications:</b> {data.implications}</p>}
      {data.recommended_next_steps && <p><b>Next steps:</b> {data.recommended_next_steps.join(" • ")}</p>}
    </div>;
  }
  if (type === "x") return <div className="thread">{data.posts?.map((x,i)=><div key={i}><span>{i+1}</span>{x}</div>)}</div>;
  if (type === "advisory") return <div className="sections">
    {data.priority && <div><b>Priority</b><p>{data.priority}</p></div>}
    {data.situation && <div><b>Situation</b><p>{data.situation}</p></div>}
    {data.key_findings && <div><b>Key Findings</b><p>{data.key_findings.join(" • ")}</p></div>}
    {data.impact && <div><b>Impact</b><p>{data.impact}</p></div>}
    {data.recommended_actions && <div><b>Recommended Actions</b><p>{data.recommended_actions.join(" • ")}</p></div>}
  </div>;
  if (type === "presentation") return <div className="slides">{data.slides?.map((s,i)=><div className="slideMini" key={i}><b>{i+1}. {s.title}</b><ul>{s.bullets?.map((b,j)=><li key={j}>{b}</li>)}</ul></div>)}</div>;
  if (type === "infographic") return <div className="sections">{data.sections?.map((s,i)=><div key={i}><b>{s.label}</b><p>{s.points?.join(" • ")}</p></div>)}</div>;
  if (type === "video") return <div className="sections">
    <p><b>Duration:</b> {data.duration}</p>
    {data.opening_hook && <p><b>Hook:</b> {data.opening_hook}</p>}
    {data.scenes?.map(s=><div key={s.scene}>
      <b>Scene {s.scene} — {s.duration}</b>
      <p><b>Visual:</b> {s.visual}</p>
      <p><b>Narration:</b> {s.narration}</p>
      {s.on_screen_text && <p><b>On-screen:</b> {s.on_screen_text}</p>}
    </div>)}
  </div>;
  return <pre>{JSON.stringify(data,null,2)}</pre>;
}

createRoot(document.getElementById("root")).render(<App />);
