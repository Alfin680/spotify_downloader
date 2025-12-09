import { useState, useEffect, useRef } from 'react'

function App() {
  const [url, setUrl] = useState('')
  const [logs, setLogs] = useState([])
  const [progress, setProgress] = useState(0)
  const [isDownloading, setIsDownloading] = useState(false)
  const [finalLink, setFinalLink] = useState(null)
  const logsEndRef = useRef(null)

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  const handleDownload = () => {
    if (!url) return;
    
    // --- RESET STATE FOR NEW DOWNLOAD ---
    setIsDownloading(true);
    setFinalLink(null); // <--- This hides the old download button immediately
    setLogs(['> SYSTEM: INITIALIZING NEW SESSION...', '> SYSTEM: CONNECTING TO SERVER...']);
    setProgress(0);
    // ------------------------------------

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      setLogs(prev => [...prev, '> NETWORK: CONNECTED', '> NETWORK: SENDING REQUEST']);
      ws.send(JSON.stringify({ url: url }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.status) {
        setLogs(prev => [...prev, `> ${data.status.toUpperCase()}`]);
      }
      
      if (data.progress !== undefined) {
        setProgress(data.progress);
      }
      
      if (data.download_url) {
        setLogs(prev => [
          ...prev, 
          `> SUCCESS: ARCHIVE CREATED`,
          `> WAITING FOR USER CONFIRMATION...`
        ]);
        
        setFinalLink(data.download_url);
        setIsDownloading(false);
        ws.close();
      }
      
      if (data.error) {
        setLogs(prev => [...prev, `> ERROR: ${data.error.toUpperCase()}`]);
        setIsDownloading(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      setLogs(prev => [...prev, '> CRITICAL FAILURE: BACKEND UNREACHABLE']);
      setIsDownloading(false);
    };
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative z-10 selection:bg-green-900 selection:text-white">
      <div className="w-full max-w-3xl bg-black border-2 border-green-500 p-1 rounded-lg border-neon relative">
        
        <div className="bg-green-900/20 p-4 border-b border-green-500/50 flex justify-between items-center">
          <h1 className="text-2xl font-bold tracking-widest text-neon">
            SPOTIFY_RIPPER<span className="animate-pulse">_V4.2_UNLOCKED</span>
          </h1>
        </div>

        <div className="p-8 space-y-8">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-green-600 to-green-900 rounded opacity-25 blur transition duration-1000 group-hover:opacity-75"></div>
            <div className="relative flex gap-4">
              <input
                type="text"
                placeholder="INSERT SPOTIFY URL"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full bg-black border border-green-700 p-4 text-green-400 placeholder-green-900 focus:outline-none focus:border-green-400 font-mono tracking-wider"
              />
              <button
                onClick={handleDownload}
                // --- THE FIX: REMOVED "|| finalLink" ---
                disabled={isDownloading} 
                className={`px-8 font-bold tracking-widest border border-green-500 uppercase ${
                  isDownloading 
                    ? 'bg-green-900/20 cursor-wait text-green-800' 
                    : 'bg-green-900/20 hover:bg-green-500 hover:text-black glitch-hover'
                }`}
              >
                {isDownloading ? 'WORKING' : 'PREPARE'}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs opacity-70">
              <span>PROGRESS</span><span>{progress}%</span>
            </div>
            <div className="h-4 bg-green-900/20 border border-green-900 w-full p-0.5">
              <div 
                className="h-full bg-green-500 shadow-[0_0_10px_#00ff41] transition-all duration-100 ease-linear"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="border border-green-800 bg-black/90 p-4 h-64 overflow-y-auto font-mono text-sm relative">
            {logs.map((log, i) => (
              <div key={i} className="mb-1 opacity-90 break-all">{log}</div>
            ))}
            <div ref={logsEndRef} />
          </div>

          {finalLink && (
            <a 
              href={finalLink}
              download
              className="block w-full text-center py-4 bg-green-600 text-black font-bold text-xl tracking-widest hover:bg-green-400 hover:shadow-[0_0_20px_#00ff41] transition-all cursor-pointer border-2 border-green-400 animate-pulse"
            >
               DOWNLOAD ZIP FILE READY (CLICK HERE) 
            </a>
          )}

        </div>
      </div>
    </div>
  )
}

export default App