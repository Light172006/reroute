import { create } from 'zustand';

interface UIState {
  selectedDayIndex: number;
  setSelectedDayIndex: (day: number) => void;

  activeTab: 'itinerary' | 'map' | 'budget' | 'agent';
  setActiveTab: (tab: 'itinerary' | 'map' | 'budget' | 'agent') => void;

  isAgentPanelOpen: boolean;
  toggleAgentPanel: () => void;
  setAgentPanelOpen: (open: boolean) => void;

  isProposalSheetOpen: boolean;
  setProposalSheetOpen: (open: boolean) => void;

  highlightedItemId: string | null;
  setHighlightedItemId: (id: string | null) => void;

  activeRunId: string | null;
  setActiveRunId: (id: string | null) => void;

  toastMessage: { text: string; type: 'success' | 'info' | 'error' | 'warning' } | null;
  setToast: (msg: { text: string; type: 'success' | 'info' | 'error' | 'warning' } | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedDayIndex: 1,
  setSelectedDayIndex: (day) => set({ selectedDayIndex: day }),

  activeTab: 'itinerary',
  setActiveTab: (tab) => set({ activeTab: tab }),

  isAgentPanelOpen: true,
  toggleAgentPanel: () => set((state) => ({ isAgentPanelOpen: !state.isAgentPanelOpen })),
  setAgentPanelOpen: (open) => set({ isAgentPanelOpen: open }),

  isProposalSheetOpen: false,
  setProposalSheetOpen: (open) => set({ isProposalSheetOpen: open }),

  highlightedItemId: null,
  setHighlightedItemId: (id) => set({ highlightedItemId: id }),

  activeRunId: null,
  setActiveRunId: (id) => set({ activeRunId: id }),

  toastMessage: null,
  setToast: (toastMessage) => set({ toastMessage }),
}));
