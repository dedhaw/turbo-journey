import AudioCaptureWrapper from './AudioCaptureWrapper';

export default function MyRecordingButton() {
  return (
    <AudioCaptureWrapper>
      {({
        status,
        isConnected,
        isRecording,
        isLoading,
        transcript,
        startRecording,
        stopRecording
      }) => (
        <div>
          <p>Status: {status}</p>
          <p>Connection: {isConnected}</p>
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
          >
            {isLoading
              ? 'Loading...'
              : isRecording
              ? 'Stop Recording'
              : 'Start Recording'}
          </button>
          {transcript && (
            <div>
              <h3>Transcript:</h3>
              <p>{transcript}</p>
            </div>
          )}
        </div>
      )}
    </AudioCaptureWrapper>
  );
}