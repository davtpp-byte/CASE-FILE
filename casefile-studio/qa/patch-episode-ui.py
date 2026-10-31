from pathlib import Path
f=Path('web/src/main.jsx');s=f.read_text()
def sub(a,b,n=1):
 global s
 assert a in s, a[:110]
 s=s.replace(a,b,n)
sub('import "./styles.css";','import "./styles.css";\nimport EpisodeSetup from "./EpisodeSetup.jsx";')
sub('(match[1].match(/\\d+/g) || []).map((n) => "S" + Number(n))','(match[1].match(/\\d+/g) || []).map((n) => "S" + n)')
sub('b.projects.find((p) => p.id === last)?.id ||','b.projects.find((p) => p.id === last && !p.is_demo)?.id ||\n          b.projects.find((p) => p.has_episode)?.id ||')
sub('          acceptProject(p);\n          setSelectedId(p.scenes[0]?.id);','          acceptProject(p);\n          if (p.episode || p.mode === "narration") setTab("setup");\n          setSelectedId(p.scenes[0]?.id);')
sub('''      setTab(
        p.scenes.length
          ? "edit"''','''      setTab(
        p.episode || p.mode === "narration" ? "setup" : p.scenes.length
          ? "edit"''')
sub('''              setTab(
                data.mode === "topic"''','''              setTab(
                data.mode === "narration" ? "setup" : data.mode === "topic"''')
sub('if (["narration", "footage"].includes(data.mode))','if (data.mode === "footage")')
sub('''            <Button
              icon={Sparkles}
              kind="produce"
              onClick={() => openTool("production")}
            >
              Produce draft
            </Button>''','''            <Button
              icon={Clapperboard}
              kind="setup-header-button"
              onClick={() => { setTab("setup"); setPlaying(false); }}
            >Episode setup</Button>
            {!project.episode?.guide && <Button
              icon={Sparkles}
              kind="produce"
              onClick={() => openTool("production")}
            >Produce draft</Button>}''')
sub('''          {[
            ["research", "Research", Search, project.sources.length],''','''          {[
            ...((project.episode || project.mode === "narration" || tab === "setup") ? [["setup", "Episode setup", FolderOpen, null]] : []),
            ["research", "Research", Search, project.sources.length],''')
sub('className={tab === key ? "active" : ""}','className={`${tab === key ? "active" : ""} ${key === "setup" ? "setup-nav" : ""}`}')
sub('''        {tab === "edit" && (
          <div className="edit-grid">''','''        {tab === "setup" && <EpisodeSetup
          key={project.id} project={project} api={api} locked={locked}
          onFlush={flushSave} onBusy={setBusy} onError={report} onNotify={notify}
          onProject={p=>{acceptProject(p); if(!p.scenes.some(s=>s.id===selectedId)){setSelectedId(p.scenes[0]?.id);setTime(0);}}}
          onNavigate={next=>{setTab(next);setPlaying(false);}}
          onRender={startRender} onNew={()=>setModal("new")}
        />}
        {tab === "edit" && (
          <div className="edit-grid">''')
sub('''                      loop
                      onLoadedMetadata''','''                      loop={!activeScene?.guide_cue_id}
                      onLoadedMetadata''')
sub('''      const expected = v.duration ? target % v.duration : target;''','''      const expected = v.duration && !activeScene?.guide_cue_id ? target % v.duration : target;''')
sub('''                  {project.captions && activeScene?.narration && (''','''                  {visual && activeScene?.source_label && <div className="film-source-label" style={{fontSize:Math.max(9,frameSize.height*.018)}}>{activeScene.source_label}</div>}
                  {project.captions && activeScene?.narration && (''')
sub('''                            <a href={ex.publication_url} download>
                              Publication notes
                            </a>''','''                            <a href={ex.publication_url} download>
                              Publication notes
                            </a>
                            {ex.episode_plan_url && <a href={ex.episode_plan_url} download>Frozen episode plan</a>}''')
start=s.index('          onExport={async (options) => {')
end=s.index('\n        />',start)
old=s[start:end]
assert old.endswith('          }}'),old[-100:]
fn=old.replace('          onExport={async (options) => {','  async function startRender(options) {',1)
fn=fn[:-len('          }}')]+'  }\n'
s=s[:start]+'          onExport={startRender}'+s[end:]
sub('  async function openTool(name, targetTab) {',fn+'\n  async function openTool(name, targetTab) {')
f.write_text(s)
