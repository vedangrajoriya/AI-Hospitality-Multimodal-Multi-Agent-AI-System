import axios from 'axios';

declare global {
  interface Window {
    __API_URL__?: string;
  }
}

// In single-service production, frontend and backend share the exact same domain.
// Fall back to relative path ("") in production so Nginx reverse-proxies directly.
const getBaseUrl = (): string => {
  if (typeof window !== 'undefined' && window.__API_URL__) {
    return window.__API_URL__;
  }

  let envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    // Fix accidental double .up.railway.app suffixes
    envUrl = envUrl.replace(/(\.up\.railway\.app)+/g, '.up.railway.app');
    // Remove trailing slash
    envUrl = envUrl.replace(/\/+$/, '');
    return envUrl;
  }

  // In production (single-container deployment), use relative path
  if (import.meta.env.PROD) {
    return '';
  }

  return 'http://localhost:8000';
};

const API_BASE_URL = getBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface TravelRequestPayload {
  destination: string;
  days: number;
  budget: string;
  preferences: string[];
}

export interface ItineraryDay {
  day: number;
  title: string;
  activities: string[];
}

export interface HotelRecommendation {
  name: string;
  category: string;
  price_range: string;
  highlights: string[];
}

export interface TravelResponse {
  destination: string;
  itinerary: ItineraryDay[];
  hotels: HotelRecommendation[];
  budget_estimate: string;
  experience_description: string;
  images: string[];
  tips: string[];
}

export const generateExperience = async (payload: TravelRequestPayload): Promise<TravelResponse> => {
  const response = await apiClient.post<TravelResponse>('/generate-experience', payload);
  return response.data;
};
