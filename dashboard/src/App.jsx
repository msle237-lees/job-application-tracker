import { useState } from 'react';
import ApplicationTable from './components/ApplicationTable';
import ApplicationForm from './components/ApplicationForm';
import Analytics from './components/Analytics';
import './App.css';

function App() {
  const [view, setView] = useState('table');
  const [editingApplication, setEditingApplication] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEdit = (application) => {
    setEditingApplication(application);
    setView('form');
  };

  const handleFormSuccess = () => {
    setEditingApplication(null);
    setView('table');
    setRefreshKey(prev => prev + 1);
  };

  const handleFormCancel = () => {
    setEditingApplication(null);
    setView('table');
  };

  const handleAddNew = () => {
    setEditingApplication(null);
    setView('form');
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎯 Job Application Tracker</h1>
        <nav className="nav-tabs">
          <button 
            className={`nav-tab ${view === 'table' ? 'active' : ''}`}
            onClick={() => setView('table')}
          >
            📋 Applications
          </button>
          <button 
            className={`nav-tab ${view === 'analytics' ? 'active' : ''}`}
            onClick={() => setView('analytics')}
          >
            📊 Analytics
          </button>
        </nav>
      </header>

      <main className="app-main">
        {view === 'table' && (
          <>
            <div className="toolbar">
              <button className="btn-primary" onClick={handleAddNew}>
                + Add Application
              </button>
            </div>
            <ApplicationTable 
              onEdit={handleEdit} 
              onRefresh={refreshKey}
            />
          </>
        )}

        {view === 'form' && (
          <ApplicationForm 
            application={editingApplication}
            onSuccess={handleFormSuccess}
            onCancel={handleFormCancel}
          />
        )}

        {view === 'analytics' && (
          <Analytics onRefresh={refreshKey} />
        )}
      </main>

      <footer className="app-footer">
        <p>Job Application Tracker v1.0.0 | Built with React + FastAPI</p>
      </footer>
    </div>
  );
}

export default App;

