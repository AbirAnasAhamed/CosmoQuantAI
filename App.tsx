import React, { useState, useCallback } from 'react';
import PublicWebsite from './screens/public/PublicWebsite';
import AppDashboard from './screens/app/AppDashboard';
import LoginTransition from './screens/app/LoginTransition';
import SignUpFormModal from './screens/public/SignUpFormModal';
// FIX: Imported AppView from types.ts to break a circular dependency.
import { AppView } from './types';

enum AppState {
  PUBLIC,
  SHOW_SIGNUP_MODAL,
  LOGGING_IN_TRANSITION,
  LOGGED_IN,
}

function App() {
  const [appState, setAppState] = useState<AppState>(AppState.PUBLIC);
  const [currentView, setCurrentView] = useState<AppView>(AppView.DASHBOARD);
  const [activeSettingsSection, setActiveSettingsSection] = useState<string | null>(null);

  const handleLoginInitiate = useCallback(() => {
    setAppState(AppState.LOGGING_IN_TRANSITION);
  }, []);

  const handleSignUpInitiate = useCallback(() => {
    setAppState(AppState.SHOW_SIGNUP_MODAL);
  }, []);

  const handleRegister = useCallback(() => {
    // After registering, go to login transition then dashboard
    setAppState(AppState.LOGGING_IN_TRANSITION);
  }, []);
  
  const handleLogout = useCallback(() => {
    setAppState(AppState.PUBLIC);
    // Also reset the view to default
    setCurrentView(AppView.DASHBOARD);
  }, []);

  const handleNavigation = useCallback((view: AppView, section?: string) => {
    setCurrentView(view);
    setActiveSettingsSection(section || null);
  }, []);

  const renderContent = () => {
    switch (appState) {
      case AppState.SHOW_SIGNUP_MODAL:
        return (
          <>
            <PublicWebsite onLogin={handleLoginInitiate} onSignUp={handleSignUpInitiate} />
            <SignUpFormModal 
              onClose={() => setAppState(AppState.PUBLIC)}
              onRegister={handleRegister}
            />
          </>
        );
      case AppState.LOGGING_IN_TRANSITION:
        return <LoginTransition onAnimationComplete={() => setAppState(AppState.LOGGED_IN)} />;
      case AppState.LOGGED_IN:
        return (
          <AppDashboard 
            currentView={currentView} 
            onNavigate={handleNavigation}
            onLogout={handleLogout}
            activeSettingsSection={activeSettingsSection}
          />
        );
      case AppState.PUBLIC:
      default:
        return <PublicWebsite onLogin={handleLoginInitiate} onSignUp={handleSignUpInitiate} />;
    }
  };
  
  return (
    <div className="min-h-screen font-sans">
      {renderContent()}
    </div>
  );
}

export default App;