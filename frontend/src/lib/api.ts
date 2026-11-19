import {
  AuthResponse,
  User,
  Trip,
  TripCreate,
  ItineraryResponse,
  ItineraryVersion,
  ProposalResponse,
  ProposalDecisionRequest,
  ProposalDecisionResponse,
  Expense,
  ExpenseCreate,
  BudgetSummary,
  ChatMessage,
  AgentRunResponse,
  SimulateRequest,
  ItineraryItem,
} from '@/types/contract';
import { mockStore } from '@/mocks/handlers';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private isRefreshing = false;

  constructor() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('reroute_access_token');
      this.refreshToken = localStorage.getItem('reroute_refresh_token');
    }
  }

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    if (typeof window !== 'undefined') {
      localStorage.setItem('reroute_access_token', access);
      localStorage.setItem('reroute_refresh_token', refresh);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('reroute_access_token');
      localStorage.removeItem('reroute_refresh_token');
    }
  }

  isAuthenticated(): boolean {
    if (USE_MOCKS) return true;
    return !!this.accessToken;
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers || {});
    if (this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }
    headers.set('Content-Type', 'application/json');

    let response = await fetch(url, { ...options, headers });

    if (response.status === 401 && this.refreshToken && !this.isRefreshing) {
      this.isRefreshing = true;
      try {
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (refreshRes.ok) {
          const data = await refreshRes.json();
          this.setTokens(data.access_token, this.refreshToken);
          headers.set('Authorization', `Bearer ${data.access_token}`);
          response = await fetch(url, { ...options, headers });
        } else {
          this.clearTokens();
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
      } catch (err) {
        this.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      } finally {
        this.isRefreshing = false;
      }
    }

    return response;
  }

  // --- Auth ---
  async signup(data: { email: string; password: string; display_name: string }): Promise<AuthResponse> {
    if (USE_MOCKS) {
      const authRes: AuthResponse = {
        access_token: 'mock-jwt-token-access',
        refresh_token: 'mock-jwt-token-refresh',
        user: {
          id: 'usr-new-mock',
          email: data.email,
          display_name: data.display_name,
          home_currency: 'INR',
          units: 'metric',
          created_at: new Date().toISOString(),
        },
      };
      this.setTokens(authRes.access_token, authRes.refresh_token);
      return authRes;
    }

    const res = await fetch(`${BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Signup failed');
    const auth = await res.json();
    this.setTokens(auth.access_token, auth.refresh_token);
    return auth;
  }

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    if (USE_MOCKS) {
      const authRes: AuthResponse = {
        access_token: 'mock-jwt-token-access',
        refresh_token: 'mock-jwt-token-refresh',
        user: mockStore.user,
      };
      this.setTokens(authRes.access_token, authRes.refresh_token);
      return authRes;
    }

    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Invalid email or password');
    const auth = await res.json();
    this.setTokens(auth.access_token, auth.refresh_token);
    return auth;
  }

  async getMe(): Promise<User> {
    if (USE_MOCKS) {
      return mockStore.user;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/me`);
    if (!res.ok) throw new Error('Failed to fetch user');
    return res.json();
  }

  // --- Trips ---
  async getTrips(): Promise<Trip[]> {
    if (USE_MOCKS) {
      return mockStore.getTrips();
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips`);
    if (!res.ok) throw new Error('Failed to fetch trips');
    return res.json();
  }

  async getTrip(id: string): Promise<Trip> {
    if (USE_MOCKS) {
      const trip = mockStore.getTrip(id);
      if (!trip) throw new Error('Trip not found');
      return trip;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${id}`);
    if (!res.ok) throw new Error('Trip not found');
    return res.json();
  }

  async createTrip(data: TripCreate): Promise<Trip> {
    if (USE_MOCKS) {
      return mockStore.createTrip(data);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create trip');
    return res.json();
  }

  async updateTrip(id: string, data: Partial<Trip>): Promise<Trip> {
    if (USE_MOCKS) {
      const trip = mockStore.updateTrip(id, data);
      if (!trip) throw new Error('Trip not found');
      return trip;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update trip');
    return res.json();
  }

  async deleteTrip(id: string): Promise<void> {
    if (USE_MOCKS) {
      mockStore.deleteTrip(id);
      return;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete trip');
  }

  // --- Itinerary ---
  async getItinerary(tripId: string): Promise<ItineraryResponse> {
    if (USE_MOCKS) {
      const itin = mockStore.getItinerary(tripId);
      if (!itin) throw new Error('Itinerary not found');
      return itin;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/itinerary`);
    if (!res.ok) throw new Error('Failed to fetch itinerary');
    return res.json();
  }

  async getVersions(tripId: string): Promise<ItineraryVersion[]> {
    if (USE_MOCKS) {
      return mockStore.getVersions(tripId);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/versions`);
    if (!res.ok) throw new Error('Failed to fetch versions');
    return res.json();
  }

  async restoreVersion(tripId: string, versionId: string): Promise<ItineraryResponse> {
    if (USE_MOCKS) {
      const itin = mockStore.restoreVersion(tripId, versionId);
      if (!itin) throw new Error('Version not found');
      return itin;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/versions/${versionId}/restore`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to restore version');
    return res.json();
  }

  async updateItem(itemId: string, patch: Partial<ItineraryItem>): Promise<ItineraryItem> {
    if (USE_MOCKS) {
      const updated = mockStore.updateItem(itemId, patch);
      if (!updated) throw new Error('Item not found');
      return updated;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error('Failed to update item');
    return res.json();
  }

  async deleteItem(itemId: string): Promise<void> {
    if (USE_MOCKS) {
      mockStore.deleteItem(itemId);
      return;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/items/${itemId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete item');
  }

  async reorderItems(tripId: string, dayIndex: number, orderedKeys: string[]): Promise<void> {
    if (USE_MOCKS) {
      mockStore.reorderItems(tripId, dayIndex, orderedKeys);
      return;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/items/reorder`, {
      method: 'POST',
      body: JSON.stringify({ day_index: dayIndex, ordered_stable_keys: orderedKeys }),
    });
    if (!res.ok) throw new Error('Failed to reorder items');
  }

  // --- Agent Runs ---
  async generatePlan(tripId: string): Promise<AgentRunResponse> {
    if (USE_MOCKS) {
      const runId = mockStore.startGenerate(tripId);
      return { run_id: runId };
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/generate`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to start plan generation');
    return res.json();
  }

  async checkPlan(tripId: string): Promise<AgentRunResponse> {
    if (USE_MOCKS) {
      const runId = mockStore.startCheck(tripId);
      return { run_id: runId };
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/check`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to trigger plan check');
    return res.json();
  }

  async sendChat(tripId: string, message: string): Promise<AgentRunResponse> {
    if (USE_MOCKS) {
      return mockStore.sendChat(tripId, message);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error('Failed to send chat message');
    return res.json();
  }

  async getChatHistory(tripId: string): Promise<ChatMessage[]> {
    if (USE_MOCKS) {
      return mockStore.getChatHistory(tripId);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/chat`);
    if (!res.ok) throw new Error('Failed to fetch chat history');
    return res.json();
  }

  // --- Proposals ---
  async getPendingProposals(tripId: string): Promise<ProposalResponse[]> {
    if (USE_MOCKS) {
      return mockStore.getProposals(tripId, 'pending');
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/proposals?status=pending`);
    if (!res.ok) throw new Error('Failed to fetch proposals');
    return res.json();
  }

  async getProposal(id: string): Promise<ProposalResponse> {
    if (USE_MOCKS) {
      const prop = mockStore.getProposal(id);
      if (!prop) throw new Error('Proposal not found');
      return prop;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/proposals/${id}`);
    if (!res.ok) throw new Error('Failed to fetch proposal');
    return res.json();
  }

  async decideProposal(
    proposalId: string,
    decision: 'approve' | 'reject' | 'alternatives',
    note?: string
  ): Promise<ProposalDecisionResponse> {
    if (USE_MOCKS) {
      return mockStore.decideProposal(proposalId, { decision, note });
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/proposals/${proposalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, note }),
    });
    if (!res.ok) throw new Error('Failed to submit proposal decision');
    return res.json();
  }

  // --- Expenses & Budget ---
  async getExpenses(tripId: string): Promise<Expense[]> {
    if (USE_MOCKS) {
      return mockStore.getExpenses(tripId);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/expenses`);
    if (!res.ok) throw new Error('Failed to fetch expenses');
    return res.json();
  }

  async addExpense(tripId: string, expense: ExpenseCreate): Promise<Expense> {
    if (USE_MOCKS) {
      return mockStore.addExpense(tripId, expense);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/expenses`, {
      method: 'POST',
      body: JSON.stringify(expense),
    });
    if (!res.ok) throw new Error('Failed to add expense');
    return res.json();
  }

  async deleteExpense(id: string): Promise<void> {
    if (USE_MOCKS) {
      mockStore.deleteExpense(id);
      return;
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/expenses/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete expense');
  }

  async getBudget(tripId: string): Promise<BudgetSummary> {
    if (USE_MOCKS) {
      return mockStore.getBudget(tripId);
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/trips/${tripId}/budget`);
    if (!res.ok) throw new Error('Failed to fetch budget');
    return res.json();
  }

  // --- Demo Simulation ---
  async simulateDisruption(req: SimulateRequest): Promise<AgentRunResponse> {
    if (USE_MOCKS) {
      const runId = mockStore.simulateDisruption(req.trip_id, req.type, req.day_index);
      return { run_id: runId };
    }
    const res = await this.fetchWithAuth(`${BASE_URL}/demo/simulate`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Failed to simulate disruption');
    return res.json();
  }
}

export const api = new ApiClient();
