/**
 * Joins one call's LiveKit room with the microphone only, and plays the other person.
 * livekit-client is loaded on demand, so pages without a call don't download it.
 */
export interface VoiceRoom {
  setMuted: (muted: boolean) => Promise<void>;
  leave: () => Promise<void>;
}

export interface VoiceRoomEvents {
  /** The other person is connected and can be heard. */
  onOtherJoined: () => void;
  /** The other person left or dropped. */
  onOtherLeft: () => void;
  /** Our own connection dropped for good. */
  onDisconnected: () => void;
}

export class MicrophoneBlockedError extends Error {}

export async function joinVoiceRoom(url: string, token: string, events: VoiceRoomEvents): Promise<VoiceRoom> {
  const { Room, RoomEvent, Track } = await import("livekit-client");
  const room = new Room({ adaptiveStream: false, dynacast: false });
  const players: HTMLMediaElement[] = [];

  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) {
      const element = track.attach();
      element.setAttribute("data-call-audio", "");
      document.body.appendChild(element);
      players.push(element);
    }
  });
  room.on(RoomEvent.ParticipantConnected, () => events.onOtherJoined());
  room.on(RoomEvent.ParticipantDisconnected, () => events.onOtherLeft());
  room.on(RoomEvent.Disconnected, () => events.onDisconnected());

  await room.connect(url, token, { autoSubscribe: true });
  try {
    await room.localParticipant.setMicrophoneEnabled(true);
  } catch (err) {
    await room.disconnect();
    if (err instanceof Error && /permission|notallowed|denied/i.test(`${err.name} ${err.message}`)) {
      throw new MicrophoneBlockedError("Allow microphone access to make calls.");
    }
    throw err;
  }
  if (room.remoteParticipants.size > 0) events.onOtherJoined();

  return {
    setMuted: async (muted) => { await room.localParticipant.setMicrophoneEnabled(!muted); },
    leave: async () => {
      players.forEach((el) => el.remove());
      await room.disconnect();
    },
  };
}
