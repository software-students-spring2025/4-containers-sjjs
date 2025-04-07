/**
 * JavaScript for the recording functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Step elements
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const step4 = document.getElementById('step-4');
    
    // Form elements
    const recordingSetupForm = document.getElementById('recording-setup-form');
    const recordingTitle = document.getElementById('recording-title');
    
    // Recording elements
    const recordingTime = document.getElementById('recording-time');
    const transcriptText = document.getElementById('transcript-text');
    const pauseResumeBtn = document.getElementById('pause-resume-btn');
    const stopRecordingBtn = document.getElementById('stop-recording-btn');
    
    // Results elements
    const summaryText = document.getElementById('summary-text');
    const fullTranscriptText = document.getElementById('full-transcript-text');
    
    // Global variables
    let mediaRecorder;
    let audioChunks = [];
    let recordingStartTime;
    let recordingTimer;
    let isPaused = false;
    let recordingId = null;
    let transcript = '';
    
    // Speech recognition setup
    let recognition = null;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        
        recognition.onresult = function(event) {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update the transcript with both final and interim results
            if (finalTranscript) {
                transcript += finalTranscript + ' ';
            }
            
            transcriptText.innerHTML = transcript + '<span style="color: #999;">' + interimTranscript + '</span>';
            transcriptText.parentNode.scrollTop = transcriptText.parentNode.scrollHeight;
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            // Handle errors gracefully
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please enable microphone access to use this feature.');
                goToStep(1);
            }
        };
    } else {
        alert('Speech recognition is not supported in this browser. Please try using Chrome or Edge.');
    }
    
    // Initialize the recording setup
    recordingSetupForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        if (!recordingTitle.value.trim()) {
            alert('Please enter a title for your recording.');
            return;
        }
        
        // Start recording process
        startRecording();
    });
    
    // Pause/Resume button functionality
    pauseResumeBtn.addEventListener('click', function() {
        if (isPaused) {
            resumeRecording();
        } else {
            pauseRecording();
        }
    });
    
    // Stop recording button functionality
    stopRecordingBtn.addEventListener('click', function() {
        stopRecording();
    });
    
    /**
     * Start the recording process
     */
    function startRecording() {
        // Create a new recording in the database
        fetch('/recordNew', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'title': recordingTitle.value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            recordingId = data.recording_id;
            
            // Request microphone access
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    // Initialize MediaRecorder
                    mediaRecorder = new MediaRecorder(stream);
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    // Start recording
                    mediaRecorder.start();
                    recordingStartTime = new Date();
                    updateRecordingTime();
                    
                    // Start speech recognition
                    if (recognition) {
                        recognition.start();
                    }
                    
                    // Move to step 2 (recording in progress)
                    goToStep(2);
                })
                .catch(error => {
                    console.error('Error accessing microphone:', error);
                    alert('Could not access microphone. Please make sure you have a microphone connected and have granted permission to use it.');
                });
        })
        .catch(error => {
            console.error('Error creating recording:', error);
            alert('An error occurred while creating the recording. Please try again.');
        });
    }
    
    /**
     * Pause the recording
     */
    function pauseRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.pause();
            if (recognition) {
                recognition.stop();
            }
            clearInterval(recordingTimer);
            isPaused = true;
            pauseResumeBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
        }
    }
    
    /**
     * Resume the recording
     */
    function resumeRecording() {
        if (mediaRecorder && mediaRecorder.state === 'paused') {
            mediaRecorder.resume();
            if (recognition) {
                recognition.start();
            }
            updateRecordingTime();
            isPaused = false;
            pauseResumeBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
        }
    }
    
    /**
     * Stop the recording and send data for processing
     */
    function stopRecording() {
        if (mediaRecorder) {
            // Stop media recorder
            if (mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            
            // Stop all tracks in the stream
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            // Stop speech recognition
            if (recognition) {
                recognition.stop();
            }
            
            // Clear recording timer
            clearInterval(recordingTimer);
            
            // Move to processing step
            goToStep(3);
            
            // Send transcript to server for processing
            fetch('/saveRecording', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'recording_id': recordingId,
                    'transcript': transcript.trim()
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Start polling for results
                checkProcessingStatus();
            })
            .catch(error => {
                console.error('Error saving recording:', error);
                alert('An error occurred while saving the recording. Please try again.');
                goToStep(1);
            });
        }
    }
    
    /**
     * Check the processing status of the recording
     */
    function checkProcessingStatus() {
        const pollInterval = setInterval(() => {
            fetch(`/getRecordingStatus/${recordingId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'completed') {
                        clearInterval(pollInterval);
                        
                        // Display results
                        summaryText.textContent = data.summary || 'No summary available';
                        fullTranscriptText.textContent = transcript;
                        
                        // Move to results step
                        goToStep(4);
                    } else if (data.status === 'error') {
                        clearInterval(pollInterval);
                        throw new Error('An error occurred during processing');
                    }
                    // Continue polling if status is 'processing'
                })
                .catch(error => {
                    clearInterval(pollInterval);
                    console.error('Error checking processing status:', error);
                    alert('An error occurred while checking the processing status. Please try again.');
                    window.location.href = '/';
                });
        }, 2000); // Poll every 2 seconds
    }
    
    /**
     * Update the recording time display
     */
    function updateRecordingTime() {
        clearInterval(recordingTimer);
        
        recordingTimer = setInterval(() => {
            const now = new Date();
            const elapsedTime = now - recordingStartTime;
            const seconds = Math.floor((elapsedTime / 1000) % 60);
            const minutes = Math.floor((elapsedTime / (1000 * 60)) % 60);
            
            recordingTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }
    
    /**
     * Navigate to a specific step in the recording process
     */
    function goToStep(stepNumber) {
        // Hide all steps
        step1.classList.remove('active');
        step2.classList.remove('active');
        step3.classList.remove('active');
        step4.classList.remove('active');
        
        // Show the selected step
        switch (stepNumber) {
            case 1:
                step1.classList.add('active');
                break;
            case 2:
                step2.classList.add('active');
                break;
            case 3:
                step3.classList.add('active');
                break;
            case 4:
                step4.classList.add('active');
                break;
        }
    }
});