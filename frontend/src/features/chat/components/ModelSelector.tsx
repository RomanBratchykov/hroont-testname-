import config from '../../../config/appearance.json';
import { useAppearance } from '../../settings/appearanceContext';
export function ModelSelector() {
  const { model, setModel } = useAppearance();
  return <div className="model-picker"><label htmlFor="chat-model" className="sr-only">Chat model (preview)</label><select id="chat-model" value={model} onChange={event => setModel(event.target.value)}>{config.models.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}</select><span>Preview</span></div>;
}
