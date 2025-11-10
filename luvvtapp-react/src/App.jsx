import React, { useState, useEffect, useRef } from 'react';
import { Heart, Send, User, Users, MessageCircle, Plus, Settings, LogOut, Sparkles, Menu, X } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

const App = () => {
  const [currentView, setCurrentView] = useState('chat');
  const [userId, setUserId] = useState(localStorage.getItem('luvvtapp_user_id') || null);
  const [userProfile, setUserProfile] = useState(null);
  const [relationships, setRelationships] = useState([]);
  const [selectedRelationship, setSelectedRelationship] = useState(null);
  const [messages, setMessages] = useState([]);
  const [adviceOpen, setAdviceOpen] = useState(false);
  const [adviceTopic, setAdviceTopic] = useState('Communication');
  const [adviceSituation, setAdviceSituation] = useState('');
  const [advicePartner, setAdvicePartner] = useState(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [adviceList, setAdviceList] = useState([]);
  const [selectedAdvice, setSelectedAdvice] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (userId) {
      loadUserProfile();
      loadRelationships();
      loadSessions();
      loadAdviceList();
    }
    loadSessions();
  }, [userId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const openSession = async (s) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/${s.session_id}/history`);
      if (res.ok) {
        const data = await res.json();
        setSessionId(s.session_id);
        // If session has partner context, reflect it in UI
        if (data.partner_profile) {
          setSelectedRelationship({ relationship_type: data.relationship_type || 'general', partner_profile: data.partner_profile });
        } else {
          setSelectedRelationship(null);
        }
        setMessages((data.messages || []).map(m => ({ role: m.role, content: m.content })));
        setCurrentView('chat');
        setSidebarOpen(false);
      }
    } catch (e) {
      console.error('Error opening session:', e);
    }
  };

  const loadUserProfile = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setUserProfile(data);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  };

  const loadRelationships = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/relationships/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setRelationships(data.relationships || []);
      }
    } catch (error) {
      console.error('Error loading relationships:', error);
    }
  };

  const loadAdviceList = async () => {
    try {
      if (!userId) return;
      const res = await fetch(`${API_BASE_URL}/api/advice/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setAdviceList(data.advice || []);
      }
    } catch (e) {
      console.error('Error loading advice list:', e);
    }
  };

  const loadSessions = async () => {
    try {
      if (!userId) return;
      const response = await fetch(`${API_BASE_URL}/api/sessions/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const createUser = async (name, email, assessment) => {
    try {
      const newUserId = `user_${Date.now()}`;
      const response = await fetch(`${API_BASE_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: newUserId,
          name,
          email,
          self_assessment: assessment
        })
      });
      
      if (response.ok) {
        setUserId(newUserId);
        localStorage.setItem('luvvtapp_user_id', newUserId);
        loadUserProfile();
      }
    } catch (error) {
      console.error('Error creating user:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMsg = { role: 'user', content: inputMessage };
    setMessages([...messages, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: inputMessage,
          relationship_type: selectedRelationship?.relationship_type || 'general',
          partner_profile: selectedRelationship?.partner_profile,
          self_assessment: userProfile?.self_assessment,
          session_id: sessionId
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitAdvice = async () => {
    if (!adviceTopic || !adviceSituation.trim()) return;
    setAdviceLoading(true);
    try {
      const payload = {
        user_id: userId,
        topic: adviceTopic,
        situation: adviceSituation.slice(0, 1000),
        partner_profile: advicePartner ? advicePartner.partner_profile : undefined,
        self_assessment: userProfile?.self_assessment
      };
      const res = await fetch(`${API_BASE_URL}/api/advice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedAdvice({ advice_id: data.advice_id, topic: data.topic, content: data.content, created_at: data.created_at });
        setAdviceOpen(false);
        setAdviceSituation('');
        setAdvicePartner(null);
        loadAdviceList();
      }
    } catch (e) {
      console.error('Advice request failed:', e);
    } finally {
      setAdviceLoading(false);
    }
  };

  const openAdvice = async (item) => {
    try {
      if (!item?.advice_id) return;
      const res = await fetch(`${API_BASE_URL}/api/advice/item/${item.advice_id}`);
      if (res.ok) {
        const full = await res.json();
        setSelectedAdvice(full);
        setCurrentView('chat');
        setSidebarOpen(false);
      }
    } catch (e) {
      console.error('Failed to open advice:', e);
    }
  };

  const deleteAdvice = async (advice_id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/advice/${advice_id}`, { method: 'DELETE' });
      if (res.ok) {
        setAdviceList(prev => prev.filter(a => a.advice_id !== advice_id));
        if (selectedAdvice?.advice_id === advice_id) setSelectedAdvice(null);
      }
    } catch (e) {
      console.error('Failed to delete advice:', e);
    }
  };

  if (!userId || !userProfile) {
    return <OnboardingScreen onComplete={createUser} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-pink-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 hover:bg-pink-50 rounded-lg transition-colors"
            >
              {sidebarOpen ? <X className="w-6 h-6 text-pink-600" /> : <Menu className="w-6 h-6 text-pink-600" />}
            </button>
            <div className="flex items-center gap-2">
              <Heart className="w-8 h-8 text-pink-500 fill-pink-500" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent">
                LuvvTapp
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-pink-100 to-purple-100 rounded-full">
              <User className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-700">{userProfile.name}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex max-w-7xl mx-auto">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 fixed lg:sticky top-[73px] left-0 h-[calc(100vh-73px)] w-80 bg-white/80 backdrop-blur-md border-r border-pink-100 p-6 transition-transform duration-300 z-40 overflow-y-auto`}>
          {/* Relationships */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <Users className="w-5 h-5 text-pink-500" />
                Relationships
              </h3>
              <button
                onClick={() => setCurrentView('addPartner')}
                title="Add Partner"
                className="p-2 hover:bg-pink-50 rounded-lg transition-colors"
              >
                <Plus className="w-5 h-5 text-pink-500" />
              </button>
            </div>
            
            <div className="space-y-2">
              {relationships.map((rel, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedRelationship(rel);
                    // start a new session for this partner context
                    setSessionId(null);
                    setMessages([]);
                    setCurrentView('chat');
                    setSidebarOpen(false);
                  }}
                  className={`w-full p-4 rounded-xl text-left transition-all ${
                    selectedRelationship?.partner_profile?.name === rel.partner_profile?.name
                      ? 'bg-gradient-to-r from-pink-100 to-purple-100 shadow-md'
                      : 'bg-pink-50 hover:bg-pink-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full flex items-center justify-center">
                      <Heart className="w-5 h-5 text-white fill-white" />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-800">{rel.partner_profile?.name}</p>
                      <p className="text-xs text-gray-600 capitalize">{rel.relationship_type}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Previous Chats */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Previous Chats</h3>
            <div className="space-y-4">
              <div>
                <div className="text-sm font-medium text-gray-600 mb-2">General</div>
                <div className="space-y-2">
                  {sessions.filter(s => (s.context_type ?? 'general') === 'general').map((s) => (
                    <button key={s.session_id}
                      onClick={() => openSession(s)}
                      className="w-full p-3 rounded-lg text-left bg-white border hover:shadow-sm transition"
                    >
                      <div className="text-sm text-gray-800">Session {s.session_id.slice(-6)}</div>
                      <div className="text-xs text-gray-500">{new Date(s.updated_at).toLocaleString()}</div>
                    </button>
                  ))}
                  {sessions.filter(s => (s.context_type ?? 'general') === 'general').length === 0 && (
                    <div className="text-xs text-gray-400">No general chats yet</div>
                  )}
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-600 mb-2">Partner</div>
                <div className="space-y-2">
                  {sessions.filter(s => s.context_type === 'partner').map((s) => (
                    <button key={s.session_id}
                      onClick={() => openSession(s)}
                      className="w-full p-3 rounded-lg text-left bg-white border hover:shadow-sm transition"
                    >
                      <div className="text-sm text-gray-800">
                        {(s.partner_profile?.name || 'Unknown')} ({s.relationship_type || 'partner'})
                      </div>
                      <div className="text-xs text-gray-500">{new Date(s.updated_at).toLocaleString()}</div>
                    </button>
                  ))}
                  {sessions.filter(s => s.context_type === 'partner').length === 0 && (
                    <div className="text-xs text-gray-400">No partner chats yet</div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Advice History */}
          <div className="mt-8">
            <h3 className="text-sm font-semibold text-gray-600 mb-3">Advice History</h3>
            <div className="space-y-2">
              {adviceList.map((a) => (
                <div key={a.advice_id} className="bg-white border rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-800">{a.topic}</div>
                      <div className="text-xs text-gray-500 truncate">{a.preview}</div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button onClick={() => openAdvice(a)} className="text-pink-600 text-xs hover:underline">Open</button>
                      <button onClick={() => deleteAdvice(a.advice_id)} className="text-gray-500 text-xs hover:underline">Delete</button>
                    </div>
                  </div>
                </div>
              ))}
              {adviceList.length === 0 && (
                <div className="text-xs text-gray-400">No advice yet</div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-600 mb-3">Quick Actions</h3>
            {[
              { icon: MessageCircle, text: 'New Chat', action: () => { setMessages([]); setSessionId(null); setCurrentView('chat'); } },
              { icon: Settings, text: 'Settings', action: () => setCurrentView('settings') },
              { icon: LogOut, text: 'Sign Out', action: () => { localStorage.removeItem('luvvtapp_user_id'); setUserId(null); } }
            ].map((item, idx) => (
              <button
                key={idx}
                onClick={item.action}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-pink-50 transition-colors"
              >
                <item.icon className="w-5 h-5 text-gray-600" />
                <span className="text-sm text-gray-700">{item.text}</span>
              </button>
            ))}
          </div>

          {/* Profile Summary */}
          <div className="mt-8 p-4 bg-gradient-to-br from-pink-50 to-purple-50 rounded-xl">
            <p className="text-xs text-gray-600 mb-2">Your Profile</p>
            {userProfile.self_assessment?.personality_type && (
              <p className="text-sm font-medium text-purple-700">🧠 {userProfile.self_assessment.personality_type}</p>
            )}
            {userProfile.self_assessment?.love_language && (
              <p className="text-sm font-medium text-pink-700">💝 {userProfile.self_assessment.love_language}</p>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 h-[calc(100vh-73px)] flex flex-col">
          {currentView === 'chat' ? (
            <>
              {/* Chat Header */}
              {selectedRelationship && (
                <div className="bg-white/80 backdrop-blur-md border-b border-pink-100 p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full flex items-center justify-center">
                      <Heart className="w-6 h-6 text-white fill-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-gray-800">{selectedRelationship.partner_profile?.name}</h2>
                      <p className="text-sm text-gray-600 capitalize">{selectedRelationship.relationship_type} • {selectedRelationship.partner_profile?.love_language || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Advice controls */}
              <div className="bg-white/80 backdrop-blur-md border-b border-pink-100 p-4 flex items-center justify-between">
                <div className="text-sm text-gray-600">Session: <span className="text-gray-800">{sessionId ? sessionId.slice(-6) : '—'}</span></div>
                <button onClick={()=>setAdviceOpen(true)} className="px-4 py-2 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 text-white text-sm hover:shadow">
                  Get Relationship Advice
                </button>
              </div>

              {adviceOpen && (
                <div className="p-4 border-b bg-white">
                  <div className="grid md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Topic</label>
                      <select value={adviceTopic} onChange={e=>setAdviceTopic(e.target.value)} className="w-full p-2 border rounded-lg">
                        {['Communication','Romance','Conflict Resolution','Trust','Intimacy','Family','Friendship','Self-growth'].map(t=> (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-xs text-gray-600 mb-1">Reference Partner (optional)</label>
                      <select value={advicePartner? (advicePartner.partner_profile?.name||'') : ''} onChange={e=>{
                        const rel = relationships.find(r => (r.partner_profile?.name||'')===e.target.value);
                        setAdvicePartner(rel||null);
                      }} className="w-full p-2 border rounded-lg">
                        <option value="">No partner</option>
                        {relationships.map((r,i)=> (
                          <option key={i} value={r.partner_profile?.name||''}>{r.partner_profile?.name||'Unknown'} ({r.relationship_type})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="mt-3">
                    <label className="block text-xs text-gray-600 mb-1">Describe your situation (max 1000 chars)</label>
                    <textarea value={adviceSituation} onChange={e=>setAdviceSituation(e.target.value.slice(0,1000))} rows={4} className="w-full p-3 border rounded-lg" placeholder="Describe what's going on..."/>
                    <div className="text-xs text-gray-400 mt-1">{adviceSituation.length}/1000</div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button onClick={submitAdvice} disabled={adviceLoading || !adviceSituation.trim()} className="px-4 py-2 rounded-lg bg-pink-600 text-white disabled:opacity-50">{adviceLoading? 'Requesting...' : 'Get Advice'}</button>
                    <button onClick={()=>{ setAdviceOpen(false); }} className="px-4 py-2 rounded-lg border">Cancel</button>
                  </div>
                </div>
              )}

              {selectedAdvice && (
                <div className="p-4 bg-gradient-to-br from-pink-50 to-purple-50 border-b">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-semibold text-gray-800">Advice • {selectedAdvice.topic}</div>
                      <div className="text-xs text-gray-500">{new Date(selectedAdvice.created_at).toLocaleString()}</div>
                    </div>
                    <button onClick={()=>setSelectedAdvice(null)} className="text-xs text-gray-500 hover:underline">Close</button>
                  </div>
                  <div className="mt-3 p-4 bg-white rounded-lg border whitespace-pre-wrap text-gray-800">{selectedAdvice.content}</div>
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-20 h-20 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full flex items-center justify-center mb-6">
                      <Sparkles className="w-10 h-10 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome to Your Relationship Coach</h2>
                    <p className="text-gray-600 mb-8 max-w-md">Ask me anything about relationships, communication, or personal growth. I'm here to help!</p>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl">
                      {[
                        { title: 'Communication', question: 'How can I communicate better with my partner?' },
                        { title: 'Date Ideas', question: 'What are some creative date ideas?' },
                        { title: 'Conflict', question: 'How do we resolve conflicts healthily?' }
                      ].map((item, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setInputMessage(item.question);
                          }}
                          className="p-4 bg-white rounded-xl border-2 border-pink-100 hover:border-pink-300 hover:shadow-md transition-all text-left"
                        >
                          <p className="font-semibold text-gray-800 mb-2">{item.title}</p>
                          <p className="text-sm text-gray-600">{item.question}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-2xl rounded-2xl px-6 py-4 ${
                          msg.role === 'user'
                            ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white'
                            : 'bg-white shadow-md text-gray-800'
                        }`}>
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {loading && (
                      <div className="flex justify-start">
                        <div className="bg-white shadow-md rounded-2xl px-6 py-4">
                          <div className="flex gap-2">
                            <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Input */}
              <div className="bg-white/80 backdrop-blur-md border-t border-pink-100 p-4">
                <div className="max-w-4xl mx-auto flex gap-3">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask your relationship coach anything..."
                    className="flex-1 px-6 py-3 rounded-full border-2 border-pink-200 focus:border-pink-400 focus:outline-none bg-white"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={loading || !inputMessage.trim()}
                    className="px-6 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-full hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </>
          ) : currentView === 'addPartner' ? (
            <AddPartnerProfileWizard
              userId={userId}
              onCancel={() => setCurrentView('settings')}
              onSaved={() => {
                loadRelationships();
                setCurrentView('settings');
              }}
            />
          ) : currentView === 'addRelationship' ? (
            <AddRelationshipView
              userId={userId}
              onBack={() => setCurrentView('chat')}
              onSuccess={() => {
                loadRelationships();
                setCurrentView('chat');
              }}
            />
          ) : (
            <SettingsView userProfile={userProfile} onBack={() => setCurrentView('chat')} onAddPartner={() => setCurrentView('addPartner')} />
          )}
        </main>
      </div>
    </div>
  );
};

const OnboardingScreen = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    personalityType: '',
    loveLanguage: '',
    communicationStyle: ''
  });

  const handleSubmit = () => {
    const assessment = {};
    if (formData.personalityType) assessment.personality_type = formData.personalityType;
    if (formData.loveLanguage) assessment.love_language = formData.loveLanguage;
    if (formData.communicationStyle) assessment.communication_style = formData.communicationStyle;
    
    onComplete(formData.name, formData.email, Object.keys(assessment).length > 0 ? assessment : null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-100 via-purple-100 to-blue-100 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white rounded-3xl shadow-2xl p-8 md:p-12">
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Heart className="w-10 h-10 text-white fill-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent mb-2">
            Welcome to LuvvTapp
          </h1>
          <p className="text-gray-600">Your AI-powered relationship coach</p>
        </div>

        {step === 1 ? (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
                placeholder="Enter your name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
                placeholder="your@email.com"
              />
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!formData.name || !formData.email}
              className="w-full py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg transition-all disabled:opacity-50"
            >
              Continue
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Personality Type (MBTI)</label>
              <select
                value={formData.personalityType}
                onChange={(e) => setFormData({ ...formData, personalityType: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
              >
                <option value="">Select one (optional)</option>
                {['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP'].map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Love Language</label>
              <select
                value={formData.loveLanguage}
                onChange={(e) => setFormData({ ...formData, loveLanguage: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
              >
                <option value="">Select one (optional)</option>
                {['Words of Affirmation', 'Quality Time', 'Receiving Gifts', 'Acts of Service', 'Physical Touch'].map(lang => (
                  <option key={lang} value={lang}>{lang}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Communication Style</label>
              <input
                type="text"
                value={formData.communicationStyle}
                onChange={(e) => setFormData({ ...formData, communicationStyle: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
                placeholder="e.g., Direct and honest (optional)"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 border-2 border-pink-300 text-pink-600 rounded-xl font-medium hover:bg-pink-50 transition-all"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                className="flex-1 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg transition-all"
              >
                Get Started
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AddRelationshipView = ({ userId, onBack, onSuccess }) => {
  const [formData, setFormData] = useState({
    type: 'romantic',
    name: '',
    personalityType: '',
    loveLanguage: '',
    interests: ''
  });

  const handleSubmit = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          relationship_type: formData.type,
          partner_profile: {
            name: formData.name,
            personality_type: formData.personalityType || undefined,
            love_language: formData.loveLanguage || undefined,
            interests: formData.interests ? formData.interests.split(',').map(i => i.trim()) : undefined
          }
        })
      });

      if (response.ok) {
        onSuccess();
      }
    } catch (error) {
      console.error('Error creating relationship:', error);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <button onClick={onBack} className="mb-6 text-pink-600 hover:text-pink-700 font-medium">
        ← Back
      </button>
      <h2 className="text-3xl font-bold text-gray-800 mb-8">Add Partner</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Relationship Type</label>
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
          >
            <option value="romantic">Romantic</option>
            <option value="friendship">Friendship</option>
            <option value="family">Family</option>
            <option value="self-growth">Self-Growth</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Their Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
            placeholder="Enter their name"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Their Personality Type</label>
          <select
            value={formData.personalityType}
            onChange={(e) => setFormData({ ...formData, personalityType: e.target.value })}
            className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
          >
            <option value="">Select one (optional)</option>
            {['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP'].map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Their Love Language</label>
          <select
            value={formData.loveLanguage}
            onChange={(e) => setFormData({ ...formData, loveLanguage: e.target.value })}
            className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
          >
            <option value="">Select one (optional)</option>
            {['Words of Affirmation', 'Quality Time', 'Receiving Gifts', 'Acts of Service', 'Physical Touch'].map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Their Interests</label>
          <input
            type="text"
            value={formData.interests}
            onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
            className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none"
            placeholder="e.g., hiking, cooking, music (comma-separated)"
          />
        </div>
        
        <button
          onClick={handleSubmit}
          disabled={!formData.name}
          className="w-full py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg transition-all disabled:opacity-50"
        >
          Add Partner
        </button>
      </div>
    </div>
  );
};

const SettingsView = ({ userProfile, onBack, onAddPartner }) => {
  return (
    <div className="p-8 max-w-2xl mx-auto">
      <button onClick={onBack} className="mb-6 text-pink-600 hover:text-pink-700 font-medium">
        ← Back
      </button>
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Settings</h2>
        <button onClick={onAddPartner} className="px-4 py-2 rounded-lg text-sm bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow">Add Partner Profile</button>
      </div>
      
      <div className="space-y-6">
        <div className="bg-white rounded-2xl p-6 shadow-md">
          <h3 className="font-semibold text-gray-800 mb-4">Profile Information</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Name:</span>
              <span className="font-medium">{userProfile.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Email:</span>
              <span className="font-medium">{userProfile.email}</span>
            </div>
            {userProfile.self_assessment?.personality_type && (
              <div className="flex justify-between">
                <span className="text-gray-600">Personality:</span>
                <span className="font-medium">{userProfile.self_assessment.personality_type}</span>
              </div>
            )}
            {userProfile.self_assessment?.love_language && (
              <div className="flex justify-between">
                <span className="text-gray-600">Love Language:</span>
                <span className="font-medium">{userProfile.self_assessment.love_language}</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="bg-pink-50 rounded-2xl p-6">
          <p className="text-sm text-gray-600">
            💙 <strong>Remember:</strong> I'm an AI relationship coach — I can guide and support you, but I'm not a licensed therapist. For serious mental health concerns, please reach out to a qualified professional.
          </p>
        </div>
      </div>
    </div>
  );
};

function AddPartnerProfileWizard({ userId, onCancel, onSaved }){
  const [step, setStep] = useState(1);
  const total = 3;
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    // Step 1 (mandatory)
    name: '',
    birthday: '',
    relationship_status: 'romantic',
    // Step 2 (optional)
    anniversary_dates: '', // comma-separated
    love_language: '',
    zodiac_sign: '',
    music_preferences: '',
    religious_beliefs: '',
    ideal_vacations: '',
    hobbies: '',
    fashion_preferences: '',
    dietary_restrictions: '',
  });

  const next = () => {
    if (step === 1) {
      if (!form.name.trim() || !form.birthday || !form.relationship_status) return;
    }
    setStep(Math.min(step+1, total));
  };
  const prev = () => setStep(Math.max(step-1, 1));

  const submit = async () => {
    try {
      setSaving(true);
      const relationship_type = form.relationship_status; // map directly
      const partner_profile = {
        name: form.name,
        love_language: form.love_language || undefined,
        interests: form.hobbies ? form.hobbies.split(',').map(s=>s.trim()).filter(Boolean) : undefined,
        preferences: {
          birthday: form.birthday,
          anniversary_dates: form.anniversary_dates ? form.anniversary_dates.split(',').map(s=>s.trim()).filter(Boolean) : [],
          zodiac_sign: form.zodiac_sign || undefined,
          music_preferences: form.music_preferences || undefined,
          religious_beliefs: form.religious_beliefs || undefined,
          ideal_vacations: form.ideal_vacations || undefined,
          fashion_preferences: form.fashion_preferences || undefined,
          dietary_restrictions: form.dietary_restrictions || undefined,
        }
      };
      const res = await fetch(`${API_BASE_URL}/api/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, relationship_type, partner_profile })
      });
      if (res.ok) {
        onSaved();
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <button onClick={onCancel} className="text-pink-600 hover:text-pink-700 font-medium">← Cancel</button>
        <div className="text-sm text-gray-600">Step {step} of {total}</div>
      </div>

      <div className="mt-4 h-2 bg-pink-100 rounded">
        <div className="h-2 bg-gradient-to-r from-pink-500 to-purple-600 rounded" style={{width: `${(step/total)*100}%`}} />
      </div>

      {step === 1 && (
        <div className="mt-8 space-y-6">
          <h3 className="text-xl font-semibold text-gray-800">Basic Information</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name<span className="text-red-500">*</span></label>
            <input value={form.name} onChange={e=>setForm({...form, name: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" placeholder="Partner name" />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Birthday<span className="text-red-500">*</span></label>
              <input type="date" value={form.birthday} onChange={e=>setForm({...form, birthday: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Relationship status<span className="text-red-500">*</span></label>
              <select value={form.relationship_status} onChange={e=>setForm({...form, relationship_status: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none">
                <option value="romantic">Romantic</option>
                <option value="friendship">Friendship</option>
                <option value="family">Family</option>
                <option value="self-growth">Self-Growth</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={onCancel} className="flex-1 py-3 border-2 border-pink-300 text-pink-600 rounded-xl font-medium hover:bg-pink-50">Cancel</button>
            <button onClick={next} className="flex-1 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium">Save & Continue</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="mt-8 space-y-6">
          <h3 className="text-xl font-semibold text-gray-800">More About Them (optional)</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Anniversary / Important dates</label>
              <input value={form.anniversary_dates} onChange={e=>setForm({...form, anniversary_dates: e.target.value})} placeholder="e.g., 2023-02-14, 2023-05-10" className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Love language</label>
              <input value={form.love_language} onChange={e=>setForm({...form, love_language: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" placeholder="e.g., Quality Time" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Zodiac sign</label>
              <input value={form.zodiac_sign} onChange={e=>setForm({...form, zodiac_sign: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Music preferences</label>
              <input value={form.music_preferences} onChange={e=>setForm({...form, music_preferences: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Religious beliefs</label>
              <input value={form.religious_beliefs} onChange={e=>setForm({...form, religious_beliefs: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Ideal vacation types</label>
              <input value={form.ideal_vacations} onChange={e=>setForm({...form, ideal_vacations: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" placeholder="e.g., Beach, Mountains" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Hobbies and interests</label>
              <input value={form.hobbies} onChange={e=>setForm({...form, hobbies: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" placeholder="Comma-separated" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Fashion preferences</label>
              <input value={form.fashion_preferences} onChange={e=>setForm({...form, fashion_preferences: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Dietary restrictions</label>
              <input value={form.dietary_restrictions} onChange={e=>setForm({...form, dietary_restrictions: e.target.value})} className="w-full px-4 py-3 rounded-xl border-2 border-pink-200 focus:border-pink-400 focus:outline-none" />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={prev} className="flex-1 py-3 border-2 border-pink-300 text-pink-600 rounded-xl font-medium hover:bg-pink-50">Back</button>
            <button onClick={next} className="flex-1 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium">Save & Continue</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="mt-8 space-y-6">
          <h3 className="text-xl font-semibold text-gray-800">Review</h3>
          <div className="bg-white rounded-xl border p-4 grid md:grid-cols-2 gap-3 text-sm text-gray-700">
            <div><span className="font-medium">Name:</span> {form.name}</div>
            <div><span className="font-medium">Birthday:</span> {form.birthday}</div>
            <div><span className="font-medium">Relationship status:</span> {form.relationship_status}</div>
            <div><span className="font-medium">Love language:</span> {form.love_language || '—'}</div>
            <div><span className="font-medium">Zodiac sign:</span> {form.zodiac_sign || '—'}</div>
            <div><span className="font-medium">Music:</span> {form.music_preferences || '—'}</div>
            <div><span className="font-medium">Religious beliefs:</span> {form.religious_beliefs || '—'}</div>
            <div><span className="font-medium">Ideal vacations:</span> {form.ideal_vacations || '—'}</div>
            <div className="md:col-span-2"><span className="font-medium">Hobbies:</span> {form.hobbies || '—'}</div>
            <div><span className="font-medium">Fashion preferences:</span> {form.fashion_preferences || '—'}</div>
            <div><span className="font-medium">Dietary restrictions:</span> {form.dietary_restrictions || '—'}</div>
            <div className="md:col-span-2"><span className="font-medium">Anniversary dates:</span> {form.anniversary_dates || '—'}</div>
          </div>
          <div className="flex gap-3">
            <button onClick={prev} className="flex-1 py-3 border-2 border-pink-300 text-pink-600 rounded-xl font-medium hover:bg-pink-50">Back</button>
            <button onClick={submit} disabled={saving} className="flex-1 py-3 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl font-medium disabled:opacity-50">{saving? 'Saving…' : 'Save Profile'}</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;