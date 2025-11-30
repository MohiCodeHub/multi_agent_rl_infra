import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts'

const API = 'http://localhost:8000/api'

function Metric({ title, value }) {
  return (
    <div style={{background:'#eef',padding:12,borderRadius:8,minWidth:180}}>
      <div style={{fontWeight:'bold'}}>{title}</div>
      <div style={{fontSize:22}}>{value}</div>
    </div>
  )
}

export default function App(){
  const [tasks, setTasks] = useState({})
  const [resultsFiles, setResultsFiles] = useState([])
  const [selectedResult, setSelectedResult] = useState('')
  const [result, setResult] = useState({})
  const [genCount, setGenCount] = useState(2)
  const [genRetries, setGenRetries] = useState(3)
  
  const loadTasks = async ()=>{
    const res = await axios.get(`${API}/tasks`)
    setTasks(res.data || {})
  }
  const loadResultsFiles = async ()=>{
    const res = await axios.get(`${API}/results`)
    setResultsFiles(res.data || [])
    if(res.data && res.data.length){ setSelectedResult(res.data[res.data.length-1]) }
  }
  const loadResult = async (fname)=>{
    if(!fname) return
    const res = await axios.get(`${API}/results/${fname}`)
    setResult(res.data || {})
  }
  useEffect(()=>{ loadTasks(); loadResultsFiles(); },[])
  useEffect(()=>{ loadResult(selectedResult) },[selectedResult])

  const onGenerate = async ()=>{
    await axios.post(`${API}/generate`, { tasks_per_difficulty: genCount, max_retries: genRetries })
    await loadTasks()
  }

  // Collect metrics
  const metrics = Object.values(result).filter(v => typeof v==='object' && v.success_rate!==undefined)
  const avg = (key)=> metrics.length? (metrics.reduce((a,m)=>a+(m[key]||0),0)/metrics.length) : 0

  // Build tasks by site data for chart
  const tasksBySite = useMemo(()=>{
    const counts = {}
    Object.values(tasks).forEach(list => {
      (list||[]).forEach(t => {
        const site = t.site || 'unknown'
        counts[site] = (counts[site]||0) + 1
      })
    })
    return Object.entries(counts).map(([name, value])=>({ name, value }))
  }, [tasks])

  const COLORS = ['#4f46e5','#06b6d4','#22c55e','#f59e0b','#ef4444','#8b5cf6']

  return (
    <div style={{padding:24,fontFamily:'system-ui', background:'#f9fafb', minHeight:'100vh'}}>
      <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <h1 style={{margin:0}}>🤖 Multi-Agent RL Dashboard</h1>
        <div style={{fontSize:12,color:'#6b7280'}}>multi_agent_rl_infra</div>
      </header>
      <div style={{display:'flex',gap:16,alignItems:'center',margin:'12px 0', background:'#fff', padding:12, border:'1px solid #e5e7eb', borderRadius:10}}>
        <input type="number" value={genCount} min={1} onChange={e=>setGenCount(parseInt(e.target.value||'1'))} />
        <input type="number" value={genRetries} min={1} onChange={e=>setGenRetries(parseInt(e.target.value||'1'))} />
        <button onClick={onGenerate} style={{background:'#4f46e5',color:'#fff',border:'none',padding:'8px 12px',borderRadius:8,cursor:'pointer'}}>Generate Task Pool</button>
        <select value={selectedResult} onChange={e=>setSelectedResult(e.target.value)}>
          {resultsFiles.map(f=> <option key={f} value={f}>{f}</option>)}
        </select>
      </div>

      <section style={{background:'#fff', padding:12, border:'1px solid #e5e7eb', borderRadius:10}}>
      <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>
        <Metric title="Success Rate" value={`${(avg('success_rate')*100).toFixed(1)}%`} />
        <Metric title="Token Reduction" value={`${avg('token_reduction_percent').toFixed(1)}%`} />
        <Metric title="Avg Actions (actual)" value={avg('avg_actual_actions').toFixed(1)} />
        <Metric title="Avg Actions (min)" value={avg('avg_min_actions').toFixed(1)} />
        <Metric title="Avg Multi Tokens" value={avg('avg_multi_step_tokens').toFixed(0)} />
        <Metric title="Avg Single Tokens" value={avg('avg_single_step_tokens').toFixed(0)} />
        <Metric title="Avg Inference Calls" value={avg('avg_inference_calls').toFixed(1)} />
        <Metric title="Avg Expected Calls" value={avg('avg_expected_calls').toFixed(1)} />
      </div>
      </section>

      <h2 style={{marginTop:24}}>Tokens by Difficulty</h2>
      <div style={{width:'100%', height:280, background:'#fff', border:'1px solid #e5e7eb', borderRadius:10, padding:12}}>
        {metrics.length ? (
          <ResponsiveContainer>
            <BarChart data={Object.entries(result).filter(([k,v])=>typeof v==='object' && v.avg_multi_step_tokens!==undefined).map(([k,v])=>({
              difficulty: k,
              multi: v.avg_multi_step_tokens,
              single: v.avg_single_step_tokens
            }))}>
              <XAxis dataKey="difficulty" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="multi" name="Multi-step" fill="#4f46e5" />
              <Bar dataKey="single" name="Single-step" fill="#06b6d4" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{padding:12}}>No evaluation results loaded.</div>
        )}
      </div>

      <h2 style={{marginTop:24}}>Tasks</h2>
      <div style={{display:'flex',gap:24,alignItems:'stretch'}}>
        <div style={{flex:'0 0 360px'}}>
          <h3>Tasks by Site</h3>
          <div style={{width:'100%', height:240, background:'#fff', border:'1px solid #e5e7eb', borderRadius:10}}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={tasksBySite} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {tasksBySite.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      {Object.entries(tasks).sort((a,b)=>parseInt(a[0])-parseInt(b[0])).map(([diff, list])=> (
        <div key={diff} style={{marginTop:12}}>
          <h3>Difficulty {diff}</h3>
          {list.map(t=> (
            <details key={t.id} style={{background:'#fff',padding:12,borderRadius:10,marginBottom:8,border:'1px solid #e5e7eb'}}>
              <summary>{t.id} | {t.site} | {t.min_actions} actions</summary>
              <div>{t.description}</div>
              <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify({
                Validated: t.validated,
                EstimatedReplans: t.estimated_replans,
                OracleTokens: t.oracle_tokens
              }, null, 2)}</pre>
              {t.expected_actions && (
                <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(t.expected_actions, null, 2)}</pre>
              )}
            </details>
          ))}
        </div>
      ))}
    </div>
  )
}
