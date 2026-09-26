import { useState, useRef } from 'react';
import ChatPanel from './components/ChatPanel';
import FocusTimer from './components/FocusTimer';
import Sidebar from './components/Sidebar';
import ProfileSetup from './components/ProfileSetup';
import { Brain, MoreHorizontal } from 'lucide-react';

export default function App() {
  const [setupDone, setSetupDone] = useState(false);
  const [focusActive, setFocusActive] = useState(false);
  const [focusDuration, setFocusDuration] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatRef = useRef(null);

  function handleFocusStart(duration) { setFocusDuration(duration); setFocusActive(true); }
  function handleFocusEnd() { setFocusActive(false); setFocusDuration(null); }
  function handleSendFromSidebar(text) { if (chatRef.current?.sendMessage) chatRef.current.sendMessage(text); }
  function handleSetupComplete() { setSetupDone(true); }

  if (!setupDone) {
    return (
      <div className="h-full flex flex-col bg-ground">
        <header className="flex items-center justify-center px-6 py-4 border-b border-line">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <span className="text-sm font-bold text-ink tracking-tight">CogniFlow</span>
          </div>
        </header>
        <div className="flex-1 flex items-start justify-center overflow-y-auto">
          <ProfileSetup onComplete={handleSetupComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-ground">
      {focusActive && <FocusTimer duration={focusDuration} onEnd={handleFocusEnd} />}

      <header className="flex items-center justify-between px-5 py-3.5 border-b border-line bg-surface">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Brain size={16} className="text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-ink tracking-tight">CogniFlow</span>
            <span className="ml-2 text-[10px] text-muted font-medium px-1.5 py-0.5 bg-surface2 rounded-md border border-line">4 Agents</span>
          </div>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
            sidebarOpen ? 'bg-primary text-white' : 'bg-surface2 text-muted hover:text-ink border border-line'
          }`}
        >
          <MoreHorizontal size={15} />
        </button>
      </header>

      <div className="flex-1 flex overflow-hidden relative">
        <ChatPanel ref={chatRef} onFocusStart={handleFocusStart} />
        {sidebarOpen && (
          <Sidebar onClose={() => setSidebarOpen(false)} onSend={handleSendFromSidebar} />
        )}
      </div>
    </div>
  );
}