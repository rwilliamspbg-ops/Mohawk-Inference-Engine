import React from 'react';
import { Cpu, Play, Square, Loader2 } from 'lucide-react';
import { Model } from '../types';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: Model | null;
  isLoading: boolean;
  onSelect: (model: Model | null) => void;
  onLoad: (modelId: string) => Promise<void>;
  onUnload: (modelId: string) => Promise<void>;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  models,
  selectedModel,
  isLoading,
  onSelect,
  onLoad,
  onUnload,
}) => {
  return (
    <div className="p-4 border-b border-gray-700">
      <h2 className="text-sm font-semibold text-gray-400 mb-2 flex items-center gap-2">
        <Cpu className="w-4 h-4" />
        Model
      </h2>
      <select
        value={selectedModel?.id || ''}
        onChange={(e) => {
          const model = models.find(m => m.id === e.target.value) || null;
          onSelect(model);
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
        <>
          <div className="mt-2 flex gap-2">
            {selectedModel.status === 'loaded' ? (
              <button
                onClick={() => onUnload(selectedModel.id)}
                className="flex-1 bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-xs flex items-center justify-center gap-1"
              >
                <Square className="w-3 h-3" />
                Unload
              </button>
            ) : (
              <button
                onClick={() => onLoad(selectedModel.id)}
                disabled={isLoading}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-3 py-1 rounded text-xs flex items-center justify-center gap-1"
              >
                {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                Load
              </button>
            )}
          </div>
          <div className="mt-2 text-xs text-gray-400 space-y-1">
            <p>Status: <span className={selectedModel.status === 'loaded' ? 'text-green-400' : 'text-gray-400'}>{selectedModel.status}</span></p>
            <p>Parameters: {selectedModel.parameters}</p>
            <p>Quantization: {selectedModel.quantization}</p>
            <p>Size: {selectedModel.size}</p>
          </div>
        </>
      )}
    </div>
  );
};
