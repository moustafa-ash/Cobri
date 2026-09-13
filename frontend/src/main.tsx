import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AuthenticatedApp } from "./App";
import { copy } from "./i18n";
import "./styles.css";

const auth = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  audience: import.meta.env.VITE_AUTH0_AUDIENCE,
};

function AuthGate() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  if (isLoading) return <main className="center-state"><div className="skeleton-stack"><span /><span /></div></main>;
  if (!isAuthenticated) return <main className="center-state"><div className="signin-panel"><span className="brand-mark">C</span><h1>Cobri</h1><p>Build understanding one step at a time.</p><button className="primary-button" onClick={() => void loginWithRedirect({ appState: { returnTo: window.location.pathname } })}>{copy.en.signIn}</button></div></main>;
  return <AuthenticatedApp />;
}

function Root() {
  if (!auth.domain || !auth.clientId || !auth.audience) return <main className="center-state"><div className="signin-panel"><h1>{copy.en.configTitle}</h1><p>{copy.en.configBody}</p></div></main>;
  return (
    <Auth0Provider
      domain={auth.domain}
      clientId={auth.clientId}
      cacheLocation="memory"
      useRefreshTokens
      useRefreshTokensFallback={false}
      authorizationParams={{ redirect_uri: window.location.origin, audience: auth.audience }}
      onRedirectCallback={(state) => window.history.replaceState({}, document.title, state?.returnTo ?? "/")}
    >
      <AuthGate />
    </Auth0Provider>
  );
}

createRoot(document.getElementById("root")!).render(<BrowserRouter><Root /></BrowserRouter>);
