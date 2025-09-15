import { useEffect, useRef } from 'react';
import { LocalTrackPublication, RemoteTrackPublication, Room } from 'livekit-client';

export default function VideoGrid({ room }: { room: Room | null }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!room || !containerRef.current) return;

    const container = containerRef.current;
    function attachPub(pub: LocalTrackPublication | RemoteTrackPublication) {
      const track = pub.track;
      if (!track) return;
      const el = track.attach();
      el.className = 'w-full h-48 object-cover rounded-xl bg-black';
      container.appendChild(el);
    }
    function detachPub(pub: LocalTrackPublication | RemoteTrackPublication) {
      const track = pub.track;
      if (!track) return;
      track.detach().forEach(el => el.remove());
    }

    // Add null checks before accessing tracks
    if (room.localParticipant && room.localParticipant.tracks) {
      room.localParticipant.tracks.forEach(attachPub);
    }
    
    if (room.participants) {
      room.participants.forEach(p => {
        if (p.tracks) {
          p.tracks.forEach(attachPub);
        }
      });
    }

    const onTrackSubscribed = (_track: any, pub: any, _participant: any) => attachPub(pub);
    const onTrackUnsubscribed = (_track: any, pub: any, _participant: any) => detachPub(pub);

    room.on('trackSubscribed', onTrackSubscribed);
    room.on('trackUnsubscribed', onTrackUnsubscribed);

    return () => {
      room.off('trackSubscribed', onTrackSubscribed);
      room.off('trackUnsubscribed', onTrackUnsubscribed);
      container.querySelectorAll('video,audio').forEach(el => el.remove());
    };
  }, [room]);

  return (
    <div ref={containerRef} className="grid grid-cols-2 gap-3"></div>
  );
}


