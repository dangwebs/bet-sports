import { useEffect } from "react";
import { usePredictionStore } from "../application/stores/usePredictionStore";
import { useBotStore } from "../application/stores/useBotStore";
import { useLiveStore } from "../application/stores/useLiveStore";

export const useInitialization = () => {
  const { fetchLeagues, checkTrainingStatus } = usePredictionStore() as any;
  const { fetchTrainingData } = useBotStore();
  const { startPolling, stopPolling } = useLiveStore();

  useEffect(() => {
    fetchLeagues();
    fetchTrainingData(); // Check bot/training status on startup
    checkTrainingStatus(); // Check for training updates
    startPolling(30000); // Poll every 30 seconds to match backend cache TTL

    // Poll for training updates
    const trainingInterval = setInterval(checkTrainingStatus, 60000);

    return () => {
      stopPolling();
      clearInterval(trainingInterval);
    };
  }, [
    fetchLeagues,
    fetchTrainingData,
    startPolling,
    stopPolling,
    checkTrainingStatus,
  ]);
};
