import React, { useState } from 'react';
import { 
  MessageSquare, 
  Settings, 
  Play, 
  Square, 
  Plus, 
  Trash2, 
  Cpu, 
  Zap,
  Send,
  ChevronDown,
  Loader2
} from 'lucide-react';
import { useAppStore } from './store';
import { Message } from './types';

function App() {
  const [inputMessage, setInputMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  
  const {
    models,
    selectedModel,
    setSelectedModel,
    loadModel,
    unloadModel,
    sessions,
    currentSession,
    createSession,
    deleteSession,
    setCurrentSession,
    addMessage,
    settings,
    updateSettings,
    isLoading,
    isStreaming,
    setLoading,
    setStreaming,
  } = useAppStore();

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !currentSession) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    addMessage(currentSession.id, userMessage);
    setInputMessage('');
    setStreaming(true);

    // Simulate streaming response
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    const mockResponse = "This is a simulated response from the Mohawk Inference Engine. In production, this would stream tokens from the actual LLM model. The engine supports temperature control, top-p sampling, and other advanced inference parameters.";
    
    for (let i = 0; i < mockResponse.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 30));
      assistantMessage.content += mockResponse[i];
      // Update the message incrementally (in real app, this would trigger re-render)
    }

    addMessage(currentSession.id, assistantMessage);
    setStreaming(false);
  };

  const handleNewChat = () => {
    createSession();
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-500" />
            Mohawk Studio
          </h1>
        </div>

        {/* Model Selection */}
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-gray-400 mb-2 flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            Model
          </h2>
          <select
            value={selectedModel?.id || ''}
            onChange={(e) => {
              const model = models.find(m => m.id === e.target.value);
              setSelectedModel(model || null);
            }}
            className="w-full bg-gray-700 rounded px-3 py-2 text-sm"
          >
            <option value="">Select a model...</option>
            {models.map(model => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.size})
              </option>
            ))}
          </select>
          
          {selectedModel && (
            <div className="mt-2 flex gap-2">
              {selectedModel.status === 'loaded' ? (
                <button
                  onClick={() => unloadModel(selectedModel.id)}
                  className="flex-1 bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-xs"
                >
                  Unload
                </button>
              ) : (
                <button
                  onClick={() => loadModel(selectedModel.id)}
                  disabled={isLoading}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-3 py-1 rounded text-xs flex items-center justify-center gap-1"
                >
                  {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                  Load
                </button>
              )}
            </div>
          )}
          
          {selectedModel && (
            <div className="mt-2 text-xs text-gray-400">
              <p>Status: <span className={selectedModel.status === 'loaded' ? 'text-green-400' : 'text-gray-400'}>{selectedModel.status}</span></p>
              <p>Quantization: {selectedModel.quantization}</p>
            </div>
          )}
        </div>

        {/* Chat Sessions */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-sm font-semibold text-gray-400 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Chats
            </h2>
            <button
              onClick={handleNewChat}
              className="text-gray-400 hover:text-white"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-1">
            {sessions.map(session => (
              <div
                key={session.id}
                className={`group flex items-center justify-between px-3 py-2 rounded cursor-pointer ${
                  currentSession?.id === session.id
                    ? 'bg-gray-700'
                    : 'hover:bg-gray-700'
                }`}
                onClick={() => setCurrentSession(session)}
              >
                <span className="text-sm truncate flex-1">{session.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Settings Toggle */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="w-full flex items-center justify-between px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded"
          >
            <span className="text-sm flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Settings
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showSettings ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Settings Panel */}
        {showSettings && (
          <div className="bg-gray-800 border-b border-gray-700 p-4">
            <h3 className="text-lg font-semibold mb-4">Inference Settings</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Temperature</label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={settings.temperature}
                  onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <span className="text-xs text-gray-400">{settings.temperature}</span>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Top P</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={settings.topP}
                  onChange={(e) => updateSettings({ topP: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <span className="text-xs text-gray-400">{settings.topP}</span>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Top K</label>
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={settings.topK}
                  onChange={(e) => updateSettings({ topK: parseInt(e.target.value) })}
                  className="w-full"
                />
                <span className="text-xs text-gray-400">{settings.topK}</span>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Max Tokens</label>
                <input
                  type="number"
                  value={settings.maxTokens}
                  onChange={(e) => updateSettings({ maxTokens: parseInt(e.target.value) })}
                  className="w-full bg-gray-700 rounded px-2 py-1"
                />
              </div>
            </div>
            
            <div className="mt-4">
              <label className="block text-sm text-gray-400 mb-1">System Prompt</label>
              <textarea
                value={settings.systemPrompt}
                onChange={(e) => updateSettings({ systemPrompt: e.target.value })}
                className="w-full bg-gray-700 rounded px-3 py-2 h-20 resize-none"
              />
            </div>
          </div>
        )}

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4">
          {!currentSession ? (
            <div className="h-full flex items-center justify-center text-gray-400">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Select or create a chat to begin</p>
                <button
                  onClick={handleNewChat}
                  className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  New Chat
                </button>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-4">
              {currentSession.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-blue-600'
                        : 'bg-gray-700'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              {isStreaming && (
                <div className="flex justify-start">
                  <div className="bg-gray-700 rounded-lg px-4 py-3">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-700 p-4">
          <div className="max-w-4xl mx-auto flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type your message..."
              disabled={!currentSession || isStreaming}
              className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={!currentSession || !inputMessage.trim() || isStreaming}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-6 py-3 rounded-lg flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
