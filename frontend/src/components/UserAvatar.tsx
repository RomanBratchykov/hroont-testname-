import { useAppearance } from '../features/settings/appearanceContext';
import { avatars } from '../features/settings/avatars';

export function UserAvatar() {
  const { avatar } = useAppearance();
  const selected = avatars.find(option => option.id === avatar) ?? avatars[0];
  return <img className="user-avatar" src={selected.src} alt="" />;
}
