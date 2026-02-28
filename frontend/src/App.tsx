import { BrowserRouter, Routes, Route } from "react-router-dom";
import { PatientAssistantShell } from "@/features/assistant/PatientAssistantShell";
import { AppProvider, ChatProvider, VoiceProvider } from "@/store/context";
import { MetricsPage } from "./pages/MetricsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main Assistant Route */}
        <Route
          path="/"
          element={
            <AppProvider>
              <ChatProvider>
                <VoiceProvider>
                  <PatientAssistantShell />
                </VoiceProvider>
              </ChatProvider>
            </AppProvider>
          }
        />
        
        {/* Metrics Dashboard Route */}
        <Route path="/metrics" element={<MetricsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
