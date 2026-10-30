export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', nativeLabel: 'English', htmlLang: 'en' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी', htmlLang: 'hi' },
  { code: 'kn', label: 'Kannada', nativeLabel: 'ಕನ್ನಡ', htmlLang: 'kn' },
]

export const translations = {
  en: {
    ui: {
      select_level: 'Select your class level',
      select_subject: 'Select subject',
      select_topic: 'Select topic',
      enter_answer: 'Enter your answer',
      speak: 'Speak your answer',
      submit: 'Check my understanding',
      misconception_label: 'What we found',
      explanation_label: 'Here is the correction',
      visual_label: 'Visual explanation',
      suggestion_label: 'What to do next',
    },
    misconception_types: {
      partial_understanding: 'Partial Understanding',
      wrong_concept: 'Wrong Concept',
      conceptual_error: 'Conceptual Error',
      formula_misuse: 'Formula Misuse',
      step_error: 'Step Error',
      derivation_error: 'Derivation Error',
      no_misconception: 'Correct!',
    },
    suggestions: {
      retry: 'Try again with this hint',
      peer_learning: 'Discuss with a classmate',
      teacher_flag: 'Ask your teacher',
      advance: 'Great! Move to next topic',
    },
  },
  hi: {
    ui: {
      select_level: 'अपनी कक्षा का स्तर चुनें',
      select_subject: 'विषय चुनें',
      select_topic: 'टॉपिक चुनें',
      enter_answer: 'अपना उत्तर दर्ज करें',
      speak: 'अपना उत्तर बोलें',
      submit: 'मेरी समझ जांचें',
      misconception_label: 'हमें क्या मिला',
      explanation_label: 'यह सुधार है',
      visual_label: 'दृश्य व्याख्या',
      suggestion_label: 'आगे क्या करना है',
    },
    misconception_types: {
      partial_understanding: 'आंशिक समझ',
      wrong_concept: 'गलत अवधारणा',
      conceptual_error: 'अवधारणात्मक त्रुटि',
      formula_misuse: 'सूत्र का गलत उपयोग',
      step_error: 'चरण की त्रुटि',
      derivation_error: 'व्युत्पत्ति की त्रुटि',
      no_misconception: 'सही!',
    },
    suggestions: {
      retry: 'इस संकेत के साथ फिर प्रयास करें',
      peer_learning: 'किसी सहपाठी से चर्चा करें',
      teacher_flag: 'अपने शिक्षक से पूछें',
      advance: 'बहुत बढ़िया! अगले टॉपिक पर जाएं',
    },
  },
  kn: {
    ui: {
      select_level: 'ನಿಮ್ಮ ತರಗತಿಯ ಮಟ್ಟವನ್ನು ಆಯ್ಕೆಮಾಡಿ',
      select_subject: 'ವಿಷಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ',
      select_topic: 'ವಿಷಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ',
      enter_answer: 'ನಿಮ್ಮ ಉತ್ತರವನ್ನು ನಮೂದಿಸಿ',
      speak: 'ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಹೇಳಿ',
      submit: 'ನನ್ನ ತಿಳುವಳಿಕೆಯನ್ನು ಪರಿಶೀಲಿಸಿ',
      misconception_label: 'ನಾವು ಕಂಡುಕೊಂಡದ್ದು',
      explanation_label: 'ಇಲ್ಲಿದೆ ತಿದ್ದುಪಡಿ',
      visual_label: 'ದೃಶ್ಯ ವಿವರಣೆ',
      suggestion_label: 'ಮುಂದೆ ಏನು ಮಾಡಬೇಕು',
    },
    misconception_types: {
      partial_understanding: 'ಭಾಗಶಃ ತಿಳುವಳಿಕೆ',
      wrong_concept: 'ತಪ್ಪು ಪರಿಕಲ್ಪನೆ',
      conceptual_error: 'ಪರಿಕಲ್ಪನಾ ದೋಷ',
      formula_misuse: 'ಸೂತ್ರದ ತಪ್ಪು ಬಳಕೆ',
      step_error: 'ಹಂತದ ದೋಷ',
      derivation_error: 'ವ್ಯುತ್ಪನ್ನ ದೋಷ',
      no_misconception: 'ಸರಿಯಾಗಿದೆ!',
    },
    suggestions: {
      retry: 'ಈ ಸುಳಿವಿನೊಂದಿಗೆ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ',
      peer_learning: 'ಸಹಪಾಠಿಯೊಂದಿಗೆ ಚರ್ಚಿಸಿ',
      teacher_flag: 'ನಿಮ್ಮ ಶಿಕ್ಷಕರನ್ನು ಕೇಳಿ',
      advance: 'ಅದ್ಭುತ! ಮುಂದಿನ ವಿಷಯಕ್ಕೆ ಹೋಗಿ',
    },
  },
}

export const phraseTranslations = {
  hi: {
    'Pragna Vistara': 'प्रज्ञा विस्तार',
    Home: 'होम',
    Progress: 'प्रगति',
    Review: 'समीक्षा',
    Online: 'ऑनलाइन',
    Offline: 'ऑफलाइन',
    Syncing: 'सिंक हो रहा है',
    Logout: 'लॉग आउट',
    Language: 'भाषा',
    English: 'अंग्रेज़ी',
    Hindi: 'हिन्दी',
    Kannada: 'कन्नड़',
    Student: 'विद्यार्थी',
    Validator: 'सत्यापक',
    'Sign in to your learning platform': 'अपने सीखने के प्लेटफॉर्म में साइन इन करें',
    'Username or Email': 'यूज़रनेम या ईमेल',
    Password: 'पासवर्ड',
    'Forgot password?': 'पासवर्ड भूल गए?',
    'Login as Student': 'विद्यार्थी के रूप में लॉगिन करें',
    'Login as Validator': 'सत्यापक के रूप में लॉगिन करें',
    "Don't have an account?": 'खाता नहीं है?',
    'Sign up': 'साइन अप',
    'Please fill in all fields.': 'कृपया सभी फ़ील्ड भरें.',
    'Syllabus Curriculum': 'पाठ्यक्रम',
    'Pick a class to open its syllabus dashboard.': 'पाठ्यक्रम डैशबोर्ड खोलने के लिए कक्षा चुनें.',
    Board: 'बोर्ड',
    'State Board': 'राज्य बोर्ड',
    'The extracted dataset currently covers the State Board syllabus. Other boards can be added once their PDFs are processed.': 'वर्तमान डेटा सेट राज्य बोर्ड पाठ्यक्रम को कवर करता है. अन्य बोर्ड उनकी PDF प्रोसेस होने के बाद जोड़े जा सकते हैं.',
    Levels: 'स्तर',
    'Jump into a band of classes and compare coverage.': 'कक्षाओं के समूह में जाएं और कवरेज की तुलना करें.',
    Classes: 'कक्षाएं',
    'Select one class to open the full subject breakdown and chapter visuals.': 'पूरी विषय सूची और अध्याय दृश्य खोलने के लिए एक कक्षा चुनें.',
    'Open the selected class': 'चुनी हुई कक्षा खोलें',
    'View Subjects': 'विषय देखें',
    Subjects: 'विषय',
    'Choose a class first': 'पहले कक्षा चुनें',
    'The subject visuals need a class context before they can load.': 'विषय दृश्य लोड होने से पहले कक्षा की जानकारी चाहिए.',
    'Back to class dashboard': 'कक्षा डैशबोर्ड पर वापस जाएं',
    'Back to classes': 'कक्षाओं पर वापस जाएं',
    'Open any subject to inspect textbooks, workbooks, and chapter maps.': 'पाठ्यपुस्तकें, वर्कबुक और अध्याय मानचित्र देखने के लिए कोई विषय खोलें.',
    'Browse subjects': 'विषय ब्राउज़ करें',
    'Search by subject or textbook title.': 'विषय या पाठ्यपुस्तक शीर्षक से खोजें.',
    'Search subjects...': 'विषय खोजें...',
    Open: 'खोलें',
    Back: 'वापस',
    'Source textbook:': 'स्रोत पाठ्यपुस्तक:',
    'Enter your answer': 'अपना उत्तर दर्ज करें',
    'Type your thinking here...': 'अपनी सोच यहाँ लिखें...',
    'Speak your answer': 'अपना उत्तर बोलें',
    'Listening...': 'सुना जा रहा है...',
    characters: 'अक्षर',
    Hint: 'संकेत',
    'Hide hint': 'संकेत छिपाएं',
    'Saving...': 'सेव हो रहा है...',
    'Check my understanding': 'मेरी समझ जांचें',
    'Session Complete': 'सत्र पूरा हुआ',
    'What we found': 'हमें क्या मिला',
    Confidence: 'विश्वास',
    'Here is the correction': 'यह सुधार है',
    'What to do next': 'आगे क्या करना है',
    'Visual Explanation': 'दृश्य व्याख्या',
    'Conceptual Questions': 'वैचारिक प्रश्न',
    'Misconception Check': 'गलतफहमी की जांच',
    'Catalog Not Found': 'कैटलॉग नहीं मिला',
    'Back to Selection': 'चयन पर वापस जाएं',
    'All Chapters': 'सभी अध्याय',
    'Search chapters and topics...': 'अध्याय और विषय खोजें...',
    'Interactive animations, questions, and misconception probes': 'इंटरएक्टिव एनिमेशन, प्रश्न और गलतफहमी की जांच',
    'Topic not found': 'टॉपिक नहीं मिला',
    'The requested chapter or topic does not exist.': 'अनुरोधित अध्याय या विषय मौजूद नहीं है.',
    'Back to Chapters': 'अध्यायों पर वापस जाएं',
    'I understand, continue to questions': 'मैं समझता हूँ, प्रश्नों पर जारी रखें',
    'No questions available for this topic yet.': 'इस विषय के लिए अभी तक कोई प्रश्न उपलब्ध नहीं हैं.',
    'Continue to misconception check': 'गलतफहमी जांच पर जारी रखें',
    'Show hint': 'संकेत दिखाएं',
    'Concept Coverage': 'अवधारणा कवरेज',
    'Previous': 'पिछला',
    'Next question': 'अगला प्रश्न',
    'No misconception probes available for this topic yet.': 'इस विषय के लिए अभी तक कोई गलतफहमी जांच उपलब्ध नहीं है.',
    'These probes test for common misunderstandings. Choose carefully!': 'ये जांच आम गलतफहमियों का परीक्षण करती हैं. सावधानी से चुनें!',
    'Results Summary': 'परिणाम सारांश',
    'correct': 'सही',
    'Next': 'अगला',
    'Dismiss install prompt': 'इंस्टॉल संदेश बंद करें',
  },
  kn: {
    'Pragna Vistara': 'ಪ್ರಜ್ಞಾ ವಿಸ್ತಾರ',
    Home: 'ಮುಖಪುಟ',
    Progress: 'ಪ್ರಗತಿ',
    Review: 'ವಿಮರ್ಶೆ',
    Online: 'ಆನ್‌ಲೈನ್',
    Offline: 'ಆಫ್‌ಲೈನ್',
    Syncing: 'ಸಿಂಕ್ ಆಗುತ್ತಿದೆ',
    Logout: 'ಲಾಗ್ ಔಟ್',
    Language: 'ಭಾಷೆ',
    English: 'ಇಂಗ್ಲಿಷ್',
    Hindi: 'ಹಿಂದಿ',
    Kannada: 'ಕನ್ನಡ',
    Student: 'ವಿದ್ಯಾರ್ಥಿ',
    Validator: 'ಪರಿಶೀಲಕ',
    'Sign in to your learning platform': 'ನಿಮ್ಮ ಕಲಿಕಾ ವೇದಿಕೆಗೆ ಸೈನ್ ಇನ್ ಮಾಡಿ',
    'Username or Email': 'ಬಳಕೆದಾರ ಹೆಸರು ಅಥವಾ ಇಮೇಲ್',
    Password: 'ಪಾಸ್‌ವರ್ಡ್',
    'Forgot password?': 'ಪಾಸ್‌ವರ್ಡ್ ಮರೆತಿರಾ?',
    'Login as Student': 'ವಿದ್ಯಾರ್ಥಿಯಾಗಿ ಲಾಗಿನ್ ಮಾಡಿ',
    'Login as Validator': 'ಪರಿಶೀಲಕರಾಗಿ ಲಾಗಿನ್ ಮಾಡಿ',
    "Don't have an account?": 'ಖಾತೆ ಇಲ್ಲವೇ?',
    'Sign up': 'ಸೈನ್ ಅಪ್',
    'Please fill in all fields.': 'ದಯವಿಟ್ಟು ಎಲ್ಲಾ ಕ್ಷೇತ್ರಗಳನ್ನು ತುಂಬಿ.',
    'Syllabus Curriculum': 'ಪಠ್ಯಕ್ರಮ',
    'Pick a class to open its syllabus dashboard.': 'ಪಠ್ಯಕ್ರಮ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ತೆರೆಯಲು ತರಗತಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.',
    Board: 'ಮಂಡಳಿ',
    'State Board': 'ರಾಜ್ಯ ಮಂಡಳಿ',
    'The extracted dataset currently covers the State Board syllabus. Other boards can be added once their PDFs are processed.': 'ಪ್ರಸ್ತುತ ಡೇಟಾಸೆಟ್ ರಾಜ್ಯ ಮಂಡಳಿ ಪಠ್ಯಕ್ರಮವನ್ನು ಒಳಗೊಂಡಿದೆ. ಇತರ ಮಂಡಳಿಗಳ PDF ಗಳು ಪ್ರಕ್ರಿಯೆಗೊಂಡ ನಂತರ ಅವನ್ನು ಸೇರಿಸಬಹುದು.',
    Levels: 'ಮಟ್ಟಗಳು',
    'Jump into a band of classes and compare coverage.': 'ತರಗತಿಗಳ ಗುಂಪಿಗೆ ಹೋಗಿ ವ್ಯಾಪ್ತಿಯನ್ನು ಹೋಲಿಸಿ.',
    Classes: 'ತರಗತಿಗಳು',
    'Select one class to open the full subject breakdown and chapter visuals.': 'ಪೂರ್ಣ ವಿಷಯ ವಿವರ ಮತ್ತು ಅಧ್ಯಾಯ ದೃಶ್ಯಗಳನ್ನು ತೆರೆಯಲು ಒಂದು ತರಗತಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.',
    'Open the selected class': 'ಆಯ್ಕೆ ಮಾಡಿದ ತರಗತಿಯನ್ನು ತೆರೆಯಿರಿ',
    'View Subjects': 'ವಿಷಯಗಳನ್ನು ನೋಡಿ',
    Subjects: 'ವಿಷಯಗಳು',
    'Choose a class first': 'ಮೊದಲು ತರಗತಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
    'The subject visuals need a class context before they can load.': 'ವಿಷಯ ದೃಶ್ಯಗಳು ಲೋಡ್ ಆಗಲು ಮೊದಲು ತರಗತಿಯ ಮಾಹಿತಿ ಬೇಕು.',
    'Back to class dashboard': 'ತರಗತಿ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಹಿಂದಿರುಗಿ',
    'Back to classes': 'ತರಗತಿಗಳಿಗೆ ಹಿಂದಿರುಗಿ',
    'Open any subject to inspect textbooks, workbooks, and chapter maps.': 'ಪಠ್ಯಪುಸ್ತಕಗಳು, ವರ್ಕ್‌ಬುಕ್‌ಗಳು ಮತ್ತು ಅಧ್ಯಾಯ ನಕ್ಷೆಗಳನ್ನು ನೋಡಲು ಯಾವುದಾದರೂ ವಿಷಯ ತೆರೆಯಿರಿ.',
    'Browse subjects': 'ವಿಷಯಗಳನ್ನು ಬ್ರೌಸ್ ಮಾಡಿ',
    'Search by subject or textbook title.': 'ವಿಷಯ ಅಥವಾ ಪಠ್ಯಪುಸ್ತಕ ಶೀರ್ಷಿಕೆಯಿಂದ ಹುಡುಕಿ.',
    'Search subjects...': 'ವಿಷಯಗಳನ್ನು ಹುಡುಕಿ...',
    Open: 'ತೆರೆಯಿರಿ',
    Back: 'ಹಿಂದೆ',
    'Source textbook:': 'ಮೂಲ ಪಠ್ಯಪುಸ್ತಕ:',
    'Enter your answer': 'ನಿಮ್ಮ ಉತ್ತರವನ್ನು ನಮೂದಿಸಿ',
    'Type your thinking here...': 'ನಿಮ್ಮ ಆಲೋಚನೆಯನ್ನು ಇಲ್ಲಿ ಬರೆಯಿರಿ...',
    'Speak your answer': 'ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಹೇಳಿ',
    'Listening...': 'ಕೇಳಲಾಗುತ್ತಿದೆ...',
    characters: 'ಅಕ್ಷರಗಳು',
    Hint: 'ಸುಳಿವು',
    'Hide hint': 'ಸುಳಿವು ಮರೆಮಾಡಿ',
    'Saving...': 'ಉಳಿಸಲಾಗುತ್ತಿದೆ...',
    'Check my understanding': 'ನನ್ನ ತಿಳುವಳಿಕೆಯನ್ನು ಪರಿಶೀಲಿಸಿ',
    'Session Complete': 'ಅಧಿವೇಶನ ಪೂರ್ಣಗೊಂಡಿದೆ',
    'What we found': 'ನಾವು ಕಂಡುಕೊಂಡದ್ದು',
    Confidence: 'ವಿಶ್ವಾಸ',
    'Here is the correction': 'ಇಲ್ಲಿದೆ ತಿದ್ದುಪಡಿ',
    'What to do next': 'ಮುಂದೆ ಏನು ಮಾಡಬೇಕು',
    'Visual Explanation': 'ದೃಶ್ಯ ವಿವರಣೆ',
    'Conceptual Questions': 'ಪರಿಕಲ್ಪನಾ ಪ್ರಶ್ನೆಗಳು',
    'Misconception Check': 'ತಪ್ಪು ಕಲ್ಪನೆಗಳ ತಪಾಸಣೆ',
    'Catalog Not Found': 'ಕ್ಯಾಟಲಾಗ್ ಕಂಡುಬಂದಿಲ್ಲ',
    'Back to Selection': 'ಆಯ್ಕೆಗೆ ಹಿಂತಿರುಗಿ',
    'All Chapters': 'ಎಲ್ಲಾ ಅಧ್ಯಾಯಗಳು',
    'Search chapters and topics...': 'ಅಧ್ಯಾಯಗಳು ಮತ್ತು ವಿಷಯಗಳನ್ನು ಹುಡುಕಿ...',
    'Interactive animations, questions, and misconception probes': 'ಪರಸ್ಪರ ಅನಿಮೇಷನ್‌ಗಳು, ಪ್ರಶ್ನೆಗಳು ಮತ್ತು ತಪ್ಪು ಕಲ್ಪನೆಗಳ ತಪಾಸಣೆ',
    'Topic not found': 'ವಿಷಯ ಕಂಡುಬಂದಿಲ್ಲ',
    'The requested chapter or topic does not exist.': 'ವಿನಂತಿಸಿದ ಅಧ್ಯಾಯ ಅಥವಾ ವಿಷಯ ಅಸ್ತಿತ್ವದಲ್ಲಿಲ್ಲ.',
    'Back to Chapters': 'ಅಧ್ಯಾಯಗಳಿಗೆ ಹಿಂತಿರುಗಿ',
    'I understand, continue to questions': 'ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡೆ, ಪ್ರಶ್ನೆಗಳಿಗೆ ಮುಂದುವರಿಯಿರಿ',
    'No questions available for this topic yet.': 'ಈ ವಿಷಯಕ್ಕೆ ಇನ್ನೂ ಯಾವುದೇ ಪ್ರಶ್ನೆಗಳು ಲಭ್ಯವಿಲ್ಲ.',
    'Continue to misconception check': 'ತಪ್ಪು ಕಲ್ಪನೆಗಳ ತಪಾಸಣೆಗೆ ಮುಂದುವರಿಯಿರಿ',
    'Show hint': 'ಸುಳಿವು ತೋರಿಸಿ',
    'Concept Coverage': 'ಪರಿಕಲ್ಪನೆ ವ್ಯಾಪ್ತಿ',
    'Previous': 'ಹಿಂದಿನ',
    'Next question': 'ಮುಂದಿನ ಪ್ರಶ್ನೆ',
    'No misconception probes available for this topic yet.': 'ಈ ವಿಷಯಕ್ಕೆ ಇನ್ನೂ ಯಾವುದೇ ತಪ್ಪು ಕಲ್ಪನೆಗಳ ತಪಾಸಣೆ ಲಭ್ಯವಿಲ್ಲ.',
    'These probes test for common misunderstandings. Choose carefully!': 'ಈ ತಪಾಸಣೆಗಳು ಸಾಮಾನ್ಯ ತಪ್ಪು ತಿಳುವಳಿಕೆಗಳನ್ನು ಪರೀಕ್ಷಿಸುತ್ತವೆ. ಎಚ್ಚರಿಕೆಯಿಂದ ಆರಿಸಿ!',
    'Results Summary': 'ಫಲಿತಾಂಶಗಳ ಸಾರಾಂಶ',
    'correct': 'ಸರಿ',
    'Next': 'ಮುಂದಿನ',
    'Dismiss install prompt': 'ಇನ್‌ಸ್ಟಾಲ್ ಸಂದೇಶ ಮುಚ್ಚಿ',
  },
}

const termTranslations = {
  hi: {
    'Practice this section or drill into its subtopics': 'इस सेक्शन का अभ्यास करें या इसके उप-विषयों में जाएं',
    'Ready for a focused practice prompt': 'केंद्रित अभ्यास प्रश्न के लिए तैयार',
    'Review every extracted document in this subject, compare chapter density, and open a visual map of the full table of contents': 'इस विषय के हर निकाले गए दस्तावेज़ की समीक्षा करें, अध्याय घनत्व की तुलना करें, और पूरी विषय-सूची का दृश्य मानचित्र खोलें',
    'A quick view of how this subject is split across textbooks, readers, and workbooks': 'यह विषय पाठ्यपुस्तकों, रीडर और वर्कबुक में कैसे विभाजित है इसका त्वरित दृश्य',
    'Each card reflects a textbook or workbook extracted from the syllabus dataset': 'हर कार्ड पाठ्यक्रम डेटासेट से निकाली गई पाठ्यपुस्तक या वर्कबुक को दिखाता है',
    'Explore the extracted chapter structure, inspect bookmark depth, and see where this document fits inside the subject syllabus': 'निकाली गई अध्याय संरचना देखें, बुकमार्क गहराई जांचें, और देखें कि यह दस्तावेज़ विषय पाठ्यक्रम में कहाँ फिट होता है',
    'Search chapter titles, expand nested sections, and launch practice prompts directly from the extracted syllabus tree': 'अध्याय शीर्षक खोजें, nested सेक्शन खोलें, और निकाले गए पाठ्यक्रम वृक्ष से सीधे अभ्यास प्रश्न शुरू करें',
    'Useful metadata for future indexing, search, and curriculum enrichment': 'भविष्य की इंडेक्सिंग, खोज और पाठ्यक्रम सुधार के लिए उपयोगी मेटाडेटा',
    'Documents without a usable TOC should move through a second enrichment pass that infers chapter headings from extracted page text instead of relying only on PDF bookmarks': 'उपयोगी विषय-सूची के बिना दस्तावेज़ों को दूसरे सुधार चरण से गुजरना चाहिए, जो केवल PDF बुकमार्क पर निर्भर रहने के बजाय निकाले गए पृष्ठ पाठ से अध्याय शीर्षकों का अनुमान लगाता है',
    'This PDF does not expose a usable bookmark outline, so the chapter map cannot be drawn from the current extraction step alone': 'यह PDF उपयोगी बुकमार्क रूपरेखा नहीं दिखाता, इसलिए केवल वर्तमान निकासी चरण से अध्याय मानचित्र नहीं बनाया जा सकता',
    'Extract page text and headings with layout-aware parsing': 'लेआउट-सचेत पार्सिंग से पृष्ठ पाठ और शीर्षक निकालें',
    'Detect chapter titles from typography, numbering, and repetition': 'टाइपोग्राफी, क्रमांकन और दोहराव से अध्याय शीर्षक पहचानें',
    'Map inferred chapters back to page spans for progress tracking': 'प्रगति ट्रैकिंग के लिए अनुमानित अध्यायों को पृष्ठ सीमाओं से जोड़ें',
    'This practice node comes directly from the textbook syllabus tree': 'यह अभ्यास नोड सीधे पाठ्यपुस्तक पाठ्यक्रम वृक्ष से आता है',
    'We keep the document, chapter, and topic context attached so progress and explanations stay linked to the curriculum source': 'हम दस्तावेज़, अध्याय और टॉपिक संदर्भ जुड़े रखते हैं ताकि प्रगति और व्याख्याएं पाठ्यक्रम स्रोत से जुड़ी रहें',
    'This practice item stays connected to the original textbook structure': 'यह अभ्यास आइटम मूल पाठ्यपुस्तक संरचना से जुड़ा रहता है',
    'Local progress tracking from IndexedDB, built around attempts, misconception patterns, and how mastery is moving over time': 'IndexedDB से स्थानीय प्रगति ट्रैकिंग, प्रयासों, गलतफहमी पैटर्न और समय के साथ दक्षता के बदलाव पर आधारित',
    'A simple mastery curve from your last eight analyzed responses': 'आपके पिछले आठ विश्लेषित उत्तरों से सरल दक्षता वक्र',
    'Most common patterns detected in recent learning': 'हाल की सीख में पहचाने गए सबसे सामान्य पैटर्न',
    'Topics where misconception frequency and lower mastery suggest more practice': 'वे टॉपिक जहाँ गलतफहमी की आवृत्ति और कम दक्षता अधिक अभ्यास का संकेत देती है',
    'The current top pattern is': 'वर्तमान मुख्य पैटर्न है',
    'A good next step is to revisit the lowest-scoring topic and answer one fresh question in your own words': 'अच्छा अगला कदम सबसे कम स्कोर वाले टॉपिक को दोबारा देखना और अपने शब्दों में एक नया प्रश्न हल करना है',
    'chapter markers across': 'अध्याय चिह्न, कुल',
    'total TOC entries': 'कुल विषय-सूची प्रविष्टियां',
    'table of contents': 'विषय-सूची',
    'full table': 'पूरी तालिका',
    'visual map': 'दृश्य मानचित्र',
    'Interactive chapter tree': 'इंटरैक्टिव अध्याय वृक्ष',
    'Document summary': 'दस्तावेज़ सारांश',
    'Extraction quality': 'निकासी गुणवत्ता',
    'Curriculum context': 'पाठ्यक्रम संदर्भ',
    'Practice prompt': 'अभ्यास प्रश्न',
    'Student dashboard': 'विद्यार्थी डैशबोर्ड',
    'Progress at a glance': 'प्रगति एक नज़र में',
    'Improvement over time': 'समय के साथ सुधार',
    'Misconception types': 'गलतफहमी के प्रकार',
    'Weak areas': 'कमज़ोर क्षेत्र',
    'Focus next': 'आगे ध्यान दें',
    'Pipeline note': 'प्रक्रिया नोट',
    'Text extraction': 'पाठ निकासी',
    'Heading inference': 'शीर्षक अनुमान',
    'Page ranges': 'पृष्ठ सीमा',
    'Open chapter map': 'अध्याय मानचित्र खोलें',
    'Back to subjects': 'विषयों पर वापस जाएं',
    'Back to documents': 'दस्तावेज़ों पर वापस जाएं',
    'Back to syllabus dashboard': 'पाठ्यक्रम डैशबोर्ड पर वापस जाएं',
    'Back to chapter map': 'अध्याय मानचित्र पर वापस जाएं',
    'Start answering': 'उत्तर देना शुरू करें',
    'Review chapter tree': 'अध्याय वृक्ष देखें',
    'Practice more': 'और अभ्यास करें',
    'Expand all': 'सभी खोलें',
    'Reset view': 'दृश्य रीसेट करें',
    'Search chapter titles': 'अध्याय शीर्षक खोजें',
    'Search chapter titles...': 'अध्याय शीर्षक खोजें...',
    'Choose a subject first': 'पहले विषय चुनें',
    'Choose a document first': 'पहले दस्तावेज़ चुनें',
    'No embedded chapter tree yet': 'अभी कोई अंतर्निहित अध्याय वृक्ष नहीं',
    'No embedded bookmarks were found in this PDF': 'इस PDF में कोई अंतर्निहित बुकमार्क नहीं मिला',
    'No practice prompt is available for this topic yet': 'इस टॉपिक के लिए अभी कोई अभ्यास प्रश्न उपलब्ध नहीं है',
    'Could not prepare the practice prompt for this topic': 'इस टॉपिक के लिए अभ्यास प्रश्न तैयार नहीं हो सका',
    'Could not load the textbook chapter map': 'पाठ्यपुस्तक अध्याय मानचित्र लोड नहीं हो सका',
    'Could not load the subject view': 'विषय दृश्य लोड नहीं हो सका',
    'Local progress tracking': 'स्थानीय प्रगति ट्रैकिंग',
    'Questions attempted': 'प्रयास किए गए प्रश्न',
    'Average mastery': 'औसत दक्षता',
    'Improvement trend': 'सुधार प्रवृत्ति',
    'All saved locally': 'सभी स्थानीय रूप से सहेजे गए',
    'Across all attempts': 'सभी प्रयासों में',
    'Latest practice window': 'नवीनतम अभ्यास अवधि',
    'A simple mastery curve': 'सरल दक्षता वक्र',
    'Most common patterns': 'सबसे सामान्य पैटर्न',
    'No weak areas yet': 'अभी कोई कमज़ोर क्षेत्र नहीं',
    'Practice a topic': 'किसी टॉपिक का अभ्यास करें',
    'Recent attempts': 'हाल के प्रयास',
    'will show up here': 'यहाँ दिखाई देंगे',
    'after analysis runs': 'विश्लेषण चलने के बाद',
    'average mastery': 'औसत दक्षता',
    'Top misconception': 'मुख्य गलतफहमी',
    'Last practiced': 'अंतिम अभ्यास',
    'Submit a few answers': 'कुछ उत्तर जमा करें',
    'learning trend': 'सीखने की प्रवृत्ति',
    'Source textbook': 'स्रोत पाठ्यपुस्तक',
    'Source file': 'स्रोत फ़ाइल',
    'File size': 'फ़ाइल आकार',
    'Page count': 'पृष्ठ संख्या',
    'TOC entries': 'विषय-सूची प्रविष्टियां',
    'TOC docs': 'विषय-सूची दस्तावेज़',
    'Document mix': 'दस्तावेज़ मिश्रण',
    'Document coverage': 'दस्तावेज़ कवरेज',
    'Chapter density': 'अध्याय घनत्व',
    'Bookmark coverage': 'बुकमार्क कवरेज',
    'Leaf topics': 'अंतिम टॉपिक',
    'Top-level chapters': 'शीर्ष-स्तरीय अध्याय',
    'Level': 'स्तर',
    'Page': 'पृष्ठ',
    'Question': 'प्रश्न',
    'Source': 'स्रोत',
    'Subject': 'विषय',
    'Document': 'दस्तावेज़',
    'Chapter': 'अध्याय',
    'Topic path': 'टॉपिक पथ',
    'Question source': 'प्रश्न स्रोत',
    'Generated on demand': 'आवश्यकता पर बनाया गया',
    'Saved locally for offline reuse': 'ऑफलाइन पुन: उपयोग के लिए स्थानीय रूप से सहेजा गया',
    'Not linked': 'लिंक नहीं है',
    'No document id': 'दस्तावेज़ आईडी नहीं',
    'No chapter id': 'अध्याय आईडी नहीं',
    'General subject': 'सामान्य विषय',
    'Syllabus': 'पाठ्यक्रम',
    'General': 'सामान्य',
    'Unknown': 'अज्ञात',
    'Unknown file': 'अज्ञात फ़ाइल',
    'Path unavailable': 'पथ उपलब्ध नहीं',
    'Updated': 'अपडेट किया गया',
    'Books': 'पुस्तकें',
    'Book': 'पुस्तक',
    'Pages': 'पृष्ठ',
    'Entries': 'प्रविष्टियां',
    'Size': 'आकार',
    'Depth': 'गहराई',
    'Sections': 'सेक्शन',
    'Section': 'सेक्शन',
    'Topics': 'टॉपिक',
    'Topic': 'टॉपिक',
    'Markers': 'चिह्न',
    'Roots': 'मूल',
    'matches': 'मिलान',
    'extracted nodes': 'निकाले गए नोड',
    'root sections': 'मूल सेक्शन',
    'root chapters': 'मूल अध्याय',
    'Deepest level': 'सबसे गहरा स्तर',
    'terminal nodes': 'अंतिम नोड',
    'roots': 'मूल',
    'points': 'बिंदु',
    'tracked topics': 'ट्रैक किए गए टॉपिक',
    'attempts': 'प्रयास',
    'Attempts': 'प्रयास',
    'textbook': 'पाठ्यपुस्तक',
    'textbooks': 'पाठ्यपुस्तकें',
    'workbook': 'वर्कबुक',
    'workbooks': 'वर्कबुक',
    'reader': 'रीडर',
    'readers': 'रीडर',
    'chapter': 'अध्याय',
    'chapters': 'अध्याय',
    'section': 'सेक्शन',
    'sections': 'सेक्शन',
    'subtopic': 'उप-विषय',
    'subtopics': 'उप-विषय',
    'topic': 'टॉपिक',
    'topics': 'टॉपिक',
    'document': 'दस्तावेज़',
    'documents': 'दस्तावेज़',
    'pages': 'पृष्ठ',
    'page': 'पृष्ठ',
    'markers': 'चिह्न',
    'entries': 'प्रविष्टियां',
    'intensity': 'तीव्रता',
    'Practice': 'अभ्यास',
    'Review': 'समीक्षा करें',
    'review': 'समीक्षा करें',
    'every': 'हर',
    'extracted': 'निकाला गया',
    'compare': 'तुलना करें',
    'open': 'खोलें',
    'visual': 'दृश्य',
    'map': 'मानचित्र',
    'full': 'पूरा',
    'inside': 'अंदर',
    'directly': 'सीधे',
    'future': 'भविष्य',
    'indexing': 'इंडेक्सिंग',
    'metadata': 'मेटाडेटा',
    'enrichment': 'सुधार',
    'quick': 'त्वरित',
    'view': 'दृश्य',
    'split': 'विभाजित',
    'original': 'मूल',
    'structure': 'संरचना',
    'context': 'संदर्भ',
    'connected': 'जुड़ा हुआ',
    'linked': 'लिंक किया गया',
    'available': 'उपलब्ध',
    'selected': 'चुना गया',
    'current': 'वर्तमान',
    'next': 'अगला',
    'fresh': 'नया',
    'own words': 'अपने शब्दों',
    'over time': 'समय के साथ',
    'recent': 'हाल का',
    'local': 'स्थानीय',
    'saved': 'सहेजा गया',
    'offline': 'ऑफलाइन',
    'reuse': 'पुन: उपयोग',
    'practice': 'अभ्यास',
    'prompt': 'प्रश्न',
    'tree': 'वृक्ष',
    'title': 'शीर्षक',
    'titles': 'शीर्षक',
    'quality': 'गुणवत्ता',
    'coverage': 'कवरेज',
    'density': 'घनत्व',
    'inferred': 'अनुमानित',
    'structured': 'संरचित',
    'flat': 'सरल',
    'none': 'कोई नहीं',
    'high': 'उच्च',
    'medium': 'मध्यम',
    'low': 'कम',
    'Needs attention': 'ध्यान चाहिए',
    'Improving': 'सुधर रहा है',
    'Settling in': 'स्थिर हो रहा है',
    'Concept misunderstanding': 'अवधारणा की गलतफहमी',
    'Wrong logic application': 'गलत तर्क उपयोग',
    'Language misunderstanding': 'भाषा की गलतफहमी',
    'Rote memorization': 'रटकर याद करना',
    'Partial understanding': 'आंशिक समझ',
    'Class': 'कक्षा',
    'Part': 'भाग',
  },
  kn: {
    'Practice this section or drill into its subtopics': 'ಈ ವಿಭಾಗವನ್ನು ಅಭ್ಯಾಸ ಮಾಡಿ ಅಥವಾ ಉಪವಿಷಯಗಳಿಗೆ ಹೋಗಿ',
    'Ready for a focused practice prompt': 'ಕೇಂದ್ರೀಕೃತ ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆಗೆ ಸಿದ್ಧ',
    'Review every extracted document in this subject, compare chapter density, and open a visual map of the full table of contents': 'ಈ ವಿಷಯದಲ್ಲಿನ ಪ್ರತಿಯೊಂದು ಹೊರತೆಗೆದ ದಾಖಲೆಯನ್ನು ಪರಿಶೀಲಿಸಿ, ಅಧ್ಯಾಯ ಸಾಂದ್ರತೆಯನ್ನು ಹೋಲಿಸಿ, ಮತ್ತು ಸಂಪೂರ್ಣ ವಿಷಯಸೂಚಿಯ ದೃಶ್ಯ ನಕ್ಷೆ ತೆರೆಯಿರಿ',
    'A quick view of how this subject is split across textbooks, readers, and workbooks': 'ಈ ವಿಷಯವು ಪಠ್ಯಪುಸ್ತಕಗಳು, ರೀಡರ್‌ಗಳು ಮತ್ತು ವರ್ಕ್‌ಬುಕ್‌ಗಳಲ್ಲಿ ಹೇಗೆ ವಿಭಜಿಸಲಾಗಿದೆ ಎಂಬ ತ್ವರಿತ ದೃಶ್ಯ',
    'Each card reflects a textbook or workbook extracted from the syllabus dataset': 'ಪ್ರತಿ ಕಾರ್ಡ್ ಪಠ್ಯಕ್ರಮ ಡೇಟಾಸೆಟ್‌ನಿಂದ ಹೊರತೆಗೆದ ಪಠ್ಯಪುಸ್ತಕ ಅಥವಾ ವರ್ಕ್‌ಬುಕ್ ಅನ್ನು ತೋರಿಸುತ್ತದೆ',
    'Explore the extracted chapter structure, inspect bookmark depth, and see where this document fits inside the subject syllabus': 'ಹೊರತೆಗೆದ ಅಧ್ಯಾಯ ರಚನೆಯನ್ನು ಅನ್ವೇಷಿಸಿ, ಬುಕ್‌ಮಾರ್ಕ್ ಆಳವನ್ನು ಪರಿಶೀಲಿಸಿ, ಮತ್ತು ಈ ದಾಖಲೆ ವಿಷಯ ಪಠ್ಯಕ್ರಮದಲ್ಲಿ ಎಲ್ಲಿಗೆ ಸೇರುತ್ತದೆ ನೋಡಿ',
    'Search chapter titles, expand nested sections, and launch practice prompts directly from the extracted syllabus tree': 'ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆಗಳನ್ನು ಹುಡುಕಿ, ಒಳಗಿನ ವಿಭಾಗಗಳನ್ನು ವಿಸ್ತರಿಸಿ, ಮತ್ತು ಹೊರತೆಗೆದ ಪಠ್ಯಕ್ರಮ ಮರದಿಂದ ನೇರವಾಗಿ ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆಗಳನ್ನು ಆರಂಭಿಸಿ',
    'Useful metadata for future indexing, search, and curriculum enrichment': 'ಭವಿಷ್ಯದ ಸೂಚ್ಯಂಕ, ಹುಡುಕಾಟ ಮತ್ತು ಪಠ್ಯಕ್ರಮ ಸುಧಾರಣೆಗೆ ಉಪಯುಕ್ತ ಮೆಟಾಡೇಟಾ',
    'Documents without a usable TOC should move through a second enrichment pass that infers chapter headings from extracted page text instead of relying only on PDF bookmarks': 'ಬಳಸಬಹುದಾದ ವಿಷಯಸೂಚಿಯಿಲ್ಲದ ದಾಖಲೆಗಳು ಎರಡನೇ ಸುಧಾರಣಾ ಹಂತದ ಮೂಲಕ ಹೋಗಬೇಕು; ಅದು PDF ಬುಕ್‌ಮಾರ್ಕ್‌ಗಳ ಮೇಲೆ ಮಾತ್ರ ಅವಲಂಬಿಸದೆ ಹೊರತೆಗೆದ ಪುಟ ಪಠ್ಯದಿಂದ ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆಗಳನ್ನು ಊಹಿಸುತ್ತದೆ',
    'This PDF does not expose a usable bookmark outline, so the chapter map cannot be drawn from the current extraction step alone': 'ಈ PDF ಬಳಸಬಹುದಾದ ಬುಕ್‌ಮಾರ್ಕ್ ರೂಪರೇಖೆಯನ್ನು ನೀಡುವುದಿಲ್ಲ, ಆದ್ದರಿಂದ ಪ್ರಸ್ತುತ ಹೊರತೆಗೆಯುವ ಹಂತದಿಂದ ಮಾತ್ರ ಅಧ್ಯಾಯ ನಕ್ಷೆಯನ್ನು ರಚಿಸಲಾಗುವುದಿಲ್ಲ',
    'Extract page text and headings with layout-aware parsing': 'ಲೇಔಟ್ ಅರಿತ ಪಾರ್ಸಿಂಗ್ ಮೂಲಕ ಪುಟ ಪಠ್ಯ ಮತ್ತು ಶೀರ್ಷಿಕೆಗಳನ್ನು ಹೊರತೆಗೆಯಿರಿ',
    'Detect chapter titles from typography, numbering, and repetition': 'ಟೈಪೋಗ್ರಫಿ, ಸಂಖ್ಯಾಕ್ರಮ ಮತ್ತು ಪುನರಾವರ್ತನೆಯಿಂದ ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆಗಳನ್ನು ಗುರುತಿಸಿ',
    'Map inferred chapters back to page spans for progress tracking': 'ಪ್ರಗತಿ ಟ್ರ್ಯಾಕಿಂಗ್‌ಗಾಗಿ ಊಹಿಸಿದ ಅಧ್ಯಾಯಗಳನ್ನು ಪುಟ ವ್ಯಾಪ್ತಿಗಳಿಗೆ ಮ್ಯಾಪ್ ಮಾಡಿ',
    'This practice node comes directly from the textbook syllabus tree': 'ಈ ಅಭ್ಯಾಸ ನೋಡ್ ಪಠ್ಯಪುಸ್ತಕ ಪಠ್ಯಕ್ರಮ ಮರದಿಂದ ನೇರವಾಗಿ ಬರುತ್ತದೆ',
    'We keep the document, chapter, and topic context attached so progress and explanations stay linked to the curriculum source': 'ಪ್ರಗತಿ ಮತ್ತು ವಿವರಣೆಗಳು ಪಠ್ಯಕ್ರಮ ಮೂಲಕ್ಕೆ ಸಂಪರ್ಕಿತವಾಗಿರಲು ನಾವು ದಾಖಲೆ, ಅಧ್ಯಾಯ ಮತ್ತು ವಿಷಯ ಸಂದರ್ಭವನ್ನು ಜೋಡಿಸಿಕೊಂಡಿರುತ್ತೇವೆ',
    'This practice item stays connected to the original textbook structure': 'ಈ ಅಭ್ಯಾಸ ಐಟಂ ಮೂಲ ಪಠ್ಯಪುಸ್ತಕ ರಚನೆಗೆ ಸಂಪರ್ಕಿತವಾಗಿರುತ್ತದೆ',
    'Local progress tracking from IndexedDB, built around attempts, misconception patterns, and how mastery is moving over time': 'IndexedDB ನಿಂದ ಸ್ಥಳೀಯ ಪ್ರಗತಿ ಟ್ರ್ಯಾಕಿಂಗ್, ಪ್ರಯತ್ನಗಳು, ತಪ್ಪುಧಾರಣೆ ಮಾದರಿಗಳು ಮತ್ತು ಕಾಲಕ್ರಮೇಣ ಪಟ್ಟು ಹೇಗೆ ಬದಲಾಗುತ್ತಿದೆ ಎಂಬುದರ ಮೇಲೆ ನಿರ್ಮಿಸಲಾಗಿದೆ',
    'A simple mastery curve from your last eight analyzed responses': 'ನಿಮ್ಮ ಕೊನೆಯ ಎಂಟು ವಿಶ್ಲೇಷಿತ ಉತ್ತರಗಳಿಂದ ಸರಳ ಪಟ್ಟು ವಕ್ರ',
    'Most common patterns detected in recent learning': 'ಇತ್ತೀಚಿನ ಕಲಿಕೆಯಲ್ಲಿ ಕಂಡುಬಂದ ಅತ್ಯಂತ ಸಾಮಾನ್ಯ ಮಾದರಿಗಳು',
    'Topics where misconception frequency and lower mastery suggest more practice': 'ತಪ್ಪುಧಾರಣೆಗಳ ಅವಧಿ ಮತ್ತು ಕಡಿಮೆ ಪಟ್ಟು ಇನ್ನಷ್ಟು ಅಭ್ಯಾಸ ಸೂಚಿಸುವ ವಿಷಯಗಳು',
    'The current top pattern is': 'ಪ್ರಸ್ತುತ ಪ್ರಮುಖ ಮಾದರಿ',
    'A good next step is to revisit the lowest-scoring topic and answer one fresh question in your own words': 'ಉತ್ತಮ ಮುಂದಿನ ಹೆಜ್ಜೆ ಅತಿ ಕಡಿಮೆ ಅಂಕದ ವಿಷಯವನ್ನು ಮತ್ತೆ ನೋಡಿ ನಿಮ್ಮದೇ ಪದಗಳಲ್ಲಿ ಹೊಸ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸುವುದು',
    'chapter markers across': 'ಅಧ್ಯಾಯ ಗುರುತುಗಳು, ಒಟ್ಟು',
    'total TOC entries': 'ಒಟ್ಟು ವಿಷಯಸೂಚಿ ನಮೂದುಗಳು',
    'table of contents': 'ವಿಷಯಸೂಚಿ',
    'full table': 'ಸಂಪೂರ್ಣ ಪಟ್ಟಿಕೆ',
    'visual map': 'ದೃಶ್ಯ ನಕ್ಷೆ',
    'Interactive chapter tree': 'ಸಂವಹನಾತ್ಮಕ ಅಧ್ಯಾಯ ಮರ',
    'Document summary': 'ದಾಖಲೆ ಸಾರಾಂಶ',
    'Extraction quality': 'ಹೊರತೆಗೆಯುವ ಗುಣಮಟ್ಟ',
    'Curriculum context': 'ಪಠ್ಯಕ್ರಮ ಸಂದರ್ಭ',
    'Practice prompt': 'ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆ',
    'Student dashboard': 'ವಿದ್ಯಾರ್ಥಿ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
    'Progress at a glance': 'ಒಂದು ನೋಟದಲ್ಲಿ ಪ್ರಗತಿ',
    'Improvement over time': 'ಕಾಲಕ್ರಮೇಣ ಸುಧಾರಣೆ',
    'Misconception types': 'ತಪ್ಪುಧಾರಣೆಗಳ ಪ್ರಕಾರಗಳು',
    'Weak areas': 'ದುರ್ಬಲ ಕ್ಷೇತ್ರಗಳು',
    'Focus next': 'ಮುಂದೆ ಗಮನಿಸಿ',
    'Pipeline note': 'ಪ್ರಕ್ರಿಯೆ ಟಿಪ್ಪಣಿ',
    'Text extraction': 'ಪಠ್ಯ ಹೊರತೆಗೆಯುವುದು',
    'Heading inference': 'ಶೀರ್ಷಿಕೆ ಊಹೆ',
    'Page ranges': 'ಪುಟ ವ್ಯಾಪ್ತಿಗಳು',
    'Open chapter map': 'ಅಧ್ಯಾಯ ನಕ್ಷೆ ತೆರೆಯಿರಿ',
    'Back to subjects': 'ವಿಷಯಗಳಿಗೆ ಹಿಂದಿರುಗಿ',
    'Back to documents': 'ದಾಖಲೆಗಳಿಗೆ ಹಿಂದಿರುಗಿ',
    'Back to syllabus dashboard': 'ಪಠ್ಯಕ್ರಮ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಹಿಂದಿರುಗಿ',
    'Back to chapter map': 'ಅಧ್ಯಾಯ ನಕ್ಷೆಗೆ ಹಿಂದಿರುಗಿ',
    'Start answering': 'ಉತ್ತರಿಸಲು ಪ್ರಾರಂಭಿಸಿ',
    'Review chapter tree': 'ಅಧ್ಯಾಯ ಮರವನ್ನು ಪರಿಶೀಲಿಸಿ',
    'Practice more': 'ಇನ್ನಷ್ಟು ಅಭ್ಯಾಸ ಮಾಡಿ',
    'Expand all': 'ಎಲ್ಲವನ್ನು ವಿಸ್ತರಿಸಿ',
    'Reset view': 'ದೃಶ್ಯ ಮರುಹೊಂದಿಸಿ',
    'Search chapter titles': 'ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆಗಳನ್ನು ಹುಡುಕಿ',
    'Search chapter titles...': 'ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆಗಳನ್ನು ಹುಡುಕಿ...',
    'Choose a subject first': 'ಮೊದಲು ವಿಷಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ',
    'Choose a document first': 'ಮೊದಲು ದಾಖಲೆ ಆಯ್ಕೆಮಾಡಿ',
    'No embedded chapter tree yet': 'ಇನ್ನೂ ಅಂತರ್ನಿಹಿತ ಅಧ್ಯಾಯ ಮರ ಇಲ್ಲ',
    'No embedded bookmarks were found in this PDF': 'ಈ PDF ನಲ್ಲಿ ಅಂತರ್ನಿಹಿತ ಬುಕ್‌ಮಾರ್ಕ್‌ಗಳು ಕಂಡುಬಂದಿಲ್ಲ',
    'No practice prompt is available for this topic yet': 'ಈ ವಿಷಯಕ್ಕೆ ಇನ್ನೂ ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆ ಲಭ್ಯವಿಲ್ಲ',
    'Could not prepare the practice prompt for this topic': 'ಈ ವಿಷಯಕ್ಕೆ ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆ ಸಿದ್ಧಪಡಿಸಲಾಗಲಿಲ್ಲ',
    'Could not load the textbook chapter map': 'ಪಠ್ಯಪುಸ್ತಕ ಅಧ್ಯಾಯ ನಕ್ಷೆ ಲೋಡ್ ಆಗಲಿಲ್ಲ',
    'Could not load the subject view': 'ವಿಷಯ ದೃಶ್ಯ ಲೋಡ್ ಆಗಲಿಲ್ಲ',
    'Local progress tracking': 'ಸ್ಥಳೀಯ ಪ್ರಗತಿ ಟ್ರ್ಯಾಕಿಂಗ್',
    'Questions attempted': 'ಪ್ರಯತ್ನಿಸಿದ ಪ್ರಶ್ನೆಗಳು',
    'Average mastery': 'ಸರಾಸರಿ ಪಟ್ಟು',
    'Improvement trend': 'ಸುಧಾರಣೆಯ ಪ್ರವೃತ್ತಿ',
    'All saved locally': 'ಎಲ್ಲವೂ ಸ್ಥಳೀಯವಾಗಿ ಉಳಿಸಲಾಗಿದೆ',
    'Across all attempts': 'ಎಲ್ಲಾ ಪ್ರಯತ್ನಗಳಾದ್ಯಂತ',
    'Latest practice window': 'ಇತ್ತೀಚಿನ ಅಭ್ಯಾಸ ಅವಧಿ',
    'A simple mastery curve': 'ಸರಳ ಪಟ್ಟು ವಕ್ರ',
    'Most common patterns': 'ಅತ್ಯಂತ ಸಾಮಾನ್ಯ ಮಾದರಿಗಳು',
    'No weak areas yet': 'ಇನ್ನೂ ದುರ್ಬಲ ಕ್ಷೇತ್ರಗಳಿಲ್ಲ',
    'Practice a topic': 'ಒಂದು ವಿಷಯ ಅಭ್ಯಾಸ ಮಾಡಿ',
    'Recent attempts': 'ಇತ್ತೀಚಿನ ಪ್ರಯತ್ನಗಳು',
    'will show up here': 'ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತವೆ',
    'after analysis runs': 'ವಿಶ್ಲೇಷಣೆ ನಡೆದ ನಂತರ',
    'average mastery': 'ಸರಾಸರಿ ಪಟ್ಟು',
    'Top misconception': 'ಮುಖ್ಯ ತಪ್ಪುಧಾರಣೆ',
    'Last practiced': 'ಕೊನೆಯ ಅಭ್ಯಾಸ',
    'Submit a few answers': 'ಕೆಲವು ಉತ್ತರಗಳನ್ನು ಸಲ್ಲಿಸಿ',
    'learning trend': 'ಕಲಿಕೆಯ ಪ್ರವೃತ್ತಿ',
    'Source textbook': 'ಮೂಲ ಪಠ್ಯಪುಸ್ತಕ',
    'Source file': 'ಮೂಲ ಫೈಲ್',
    'File size': 'ಫೈಲ್ ಗಾತ್ರ',
    'Page count': 'ಪುಟ ಸಂಖ್ಯೆ',
    'TOC entries': 'ವಿಷಯಸೂಚಿ ನಮೂದುಗಳು',
    'TOC docs': 'ವಿಷಯಸೂಚಿ ದಾಖಲೆಗಳು',
    'Document mix': 'ದಾಖಲೆ ಮಿಶ್ರಣ',
    'Document coverage': 'ದಾಖಲೆ ವ್ಯಾಪ್ತಿ',
    'Chapter density': 'ಅಧ್ಯಾಯ ಸಾಂದ್ರತೆ',
    'Bookmark coverage': 'ಬುಕ್‌ಮಾರ್ಕ್ ವ್ಯಾಪ್ತಿ',
    'Leaf topics': 'ಅಂತಿಮ ವಿಷಯಗಳು',
    'Top-level chapters': 'ಮೇಲ್ದರ್ಜೆಯ ಅಧ್ಯಾಯಗಳು',
    'Level': 'ಮಟ್ಟ',
    'Page': 'ಪುಟ',
    'Question': 'ಪ್ರಶ್ನೆ',
    'Source': 'ಮೂಲ',
    'Subject': 'ವಿಷಯ',
    'Document': 'ದಾಖಲೆ',
    'Chapter': 'ಅಧ್ಯಾಯ',
    'Topic path': 'ವಿಷಯ ಪಥ',
    'Question source': 'ಪ್ರಶ್ನೆಯ ಮೂಲ',
    'Generated on demand': 'ಅವಶ್ಯಕತೆಯ ಮೇರೆಗೆ ರಚಿಸಲಾಗಿದೆ',
    'Saved locally for offline reuse': 'ಆಫ್‌ಲೈನ್ ಮರುಬಳಕೆಗೆ ಸ್ಥಳೀಯವಾಗಿ ಉಳಿಸಲಾಗಿದೆ',
    'Not linked': 'ಲಿಂಕ್ ಆಗಿಲ್ಲ',
    'No document id': 'ದಾಖಲೆ ಐಡಿ ಇಲ್ಲ',
    'No chapter id': 'ಅಧ್ಯಾಯ ಐಡಿ ಇಲ್ಲ',
    'General subject': 'ಸಾಮಾನ್ಯ ವಿಷಯ',
    'Syllabus': 'ಪಠ್ಯಕ್ರಮ',
    'General': 'ಸಾಮಾನ್ಯ',
    'Unknown': 'ಅಜ್ಞಾತ',
    'Unknown file': 'ಅಜ್ಞಾತ ಫೈಲ್',
    'Path unavailable': 'ಪಥ ಲಭ್ಯವಿಲ್ಲ',
    'Updated': 'ನವೀಕರಿಸಲಾಗಿದೆ',
    'Books': 'ಪುಸ್ತಕಗಳು',
    'Book': 'ಪುಸ್ತಕ',
    'Pages': 'ಪುಟಗಳು',
    'Entries': 'ನಮೂದುಗಳು',
    'Size': 'ಗಾತ್ರ',
    'Depth': 'ಆಳ',
    'Sections': 'ವಿಭಾಗಗಳು',
    'Section': 'ವಿಭಾಗ',
    'Topics': 'ವಿಷಯಗಳು',
    'Topic': 'ವಿಷಯ',
    'Markers': 'ಗುರುತುಗಳು',
    'Roots': 'ಮೂಲಗಳು',
    'matches': 'ಹೊಂದಾಣಿಕೆಗಳು',
    'extracted nodes': 'ಹೊರತೆಗೆದ ನೋಡ್‌ಗಳು',
    'root sections': 'ಮೂಲ ವಿಭಾಗಗಳು',
    'root chapters': 'ಮೂಲ ಅಧ್ಯಾಯಗಳು',
    'Deepest level': 'ಅತ್ಯಂತ ಆಳವಾದ ಮಟ್ಟ',
    'terminal nodes': 'ಅಂತಿಮ ನೋಡ್‌ಗಳು',
    'roots': 'ಮೂಲಗಳು',
    'points': 'ಬಿಂದುಗಳು',
    'tracked topics': 'ಟ್ರ್ಯಾಕ್ ಮಾಡಿದ ವಿಷಯಗಳು',
    'attempts': 'ಪ್ರಯತ್ನಗಳು',
    'Attempts': 'ಪ್ರಯತ್ನಗಳು',
    'textbook': 'ಪಠ್ಯಪುಸ್ತಕ',
    'textbooks': 'ಪಠ್ಯಪುಸ್ತಕಗಳು',
    'workbook': 'ವರ್ಕ್‌ಬುಕ್',
    'workbooks': 'ವರ್ಕ್‌ಬುಕ್‌ಗಳು',
    'reader': 'ರೀಡರ್',
    'readers': 'ರೀಡರ್‌ಗಳು',
    'chapter': 'ಅಧ್ಯಾಯ',
    'chapters': 'ಅಧ್ಯಾಯಗಳು',
    'section': 'ವಿಭಾಗ',
    'sections': 'ವಿಭಾಗಗಳು',
    'subtopic': 'ಉಪವಿಷಯ',
    'subtopics': 'ಉಪವಿಷಯಗಳು',
    'topic': 'ವಿಷಯ',
    'topics': 'ವಿಷಯಗಳು',
    'document': 'ದಾಖಲೆ',
    'documents': 'ದಾಖಲೆಗಳು',
    'pages': 'ಪುಟಗಳು',
    'page': 'ಪುಟ',
    'markers': 'ಗುರುತುಗಳು',
    'entries': 'ನಮೂದುಗಳು',
    'intensity': 'ತೀವ್ರತೆ',
    'Practice': 'ಅಭ್ಯಾಸ',
    'Review': 'ಪರಿಶೀಲಿಸಿ',
    'review': 'ಪರಿಶೀಲಿಸಿ',
    'every': 'ಪ್ರತಿ',
    'extracted': 'ಹೊರತೆಗೆದ',
    'compare': 'ಹೋಲಿಸಿ',
    'open': 'ತೆರೆಯಿರಿ',
    'visual': 'ದೃಶ್ಯ',
    'map': 'ನಕ್ಷೆ',
    'full': 'ಸಂಪೂರ್ಣ',
    'inside': 'ಒಳಗೆ',
    'directly': 'ನೇರವಾಗಿ',
    'future': 'ಭವಿಷ್ಯ',
    'indexing': 'ಸೂಚ್ಯಂಕ',
    'metadata': 'ಮೆಟಾಡೇಟಾ',
    'enrichment': 'ಸುಧಾರಣೆ',
    'quick': 'ತ್ವರಿತ',
    'view': 'ದೃಶ್ಯ',
    'split': 'ವಿಭಜಿಸಲಾಗಿದೆ',
    'original': 'ಮೂಲ',
    'structure': 'ರಚನೆ',
    'context': 'ಸಂದರ್ಭ',
    'connected': 'ಸಂಪರ್ಕಿತ',
    'linked': 'ಲಿಂಕ್ ಆಗಿದೆ',
    'available': 'ಲಭ್ಯ',
    'selected': 'ಆಯ್ಕೆ ಮಾಡಲಾಗಿದೆ',
    'current': 'ಪ್ರಸ್ತುತ',
    'next': 'ಮುಂದಿನ',
    'fresh': 'ಹೊಸ',
    'own words': 'ನಿಮ್ಮದೇ ಪದಗಳು',
    'over time': 'ಕಾಲಕ್ರಮೇಣ',
    'recent': 'ಇತ್ತೀಚಿನ',
    'local': 'ಸ್ಥಳೀಯ',
    'saved': 'ಉಳಿಸಲಾಗಿದೆ',
    'offline': 'ಆಫ್‌ಲೈನ್',
    'reuse': 'ಮರುಬಳಕೆ',
    'practice': 'ಅಭ್ಯಾಸ',
    'prompt': 'ಪ್ರಶ್ನೆ',
    'tree': 'ಮರ',
    'title': 'ಶೀರ್ಷಿಕೆ',
    'titles': 'ಶೀರ್ಷಿಕೆಗಳು',
    'quality': 'ಗುಣಮಟ್ಟ',
    'coverage': 'ವ್ಯಾಪ್ತಿ',
    'density': 'ಸಾಂದ್ರತೆ',
    'inferred': 'ಊಹಿಸಿದ',
    'structured': 'ರಚನಾತ್ಮಕ',
    'flat': 'ಸರಳ',
    'none': 'ಯಾವುದೂ ಇಲ್ಲ',
    'high': 'ಹೆಚ್ಚು',
    'medium': 'ಮಧ್ಯಮ',
    'low': 'ಕಡಿಮೆ',
    'Needs attention': 'ಗಮನ ಬೇಕು',
    'Improving': 'ಸುಧಾರಿಸುತ್ತಿದೆ',
    'Settling in': 'ಸ್ಥಿರವಾಗುತ್ತಿದೆ',
    'Concept misunderstanding': 'ಪರಿಕಲ್ಪನೆಯ ತಪ್ಪುಧಾರಣೆ',
    'Wrong logic application': 'ತಪ್ಪು ತರ್ಕ ಬಳಕೆ',
    'Language misunderstanding': 'ಭಾಷಾ ತಪ್ಪುಧಾರಣೆ',
    'Rote memorization': 'ಕಂಠಪಾಠ',
    'Partial understanding': 'ಭಾಗಶಃ ತಿಳುವಳಿಕೆ',
    'Class': 'ತರಗತಿ',
    'Part': 'ಭಾಗ',
  },
}

export function getLanguageMeta(language) {
  return SUPPORTED_LANGUAGES.find((entry) => entry.code === language) ?? SUPPORTED_LANGUAGES[0]
}

export function t(language, section, key) {
  return translations[language]?.[section]?.[key] || translations.en[section]?.[key] || key
}

export function translatePhrase(language, phrase) {
  if (language === 'en' || !phrase) return phrase

  const dictionary = phraseTranslations[language] ?? {}
  const trimmed = phrase.trim()
  const leading = phrase.match(/^\s*/)?.[0] ?? ''
  const trailing = phrase.match(/\s*$/)?.[0] ?? ''

  if (dictionary[trimmed]) {
    return `${leading}${dictionary[trimmed]}${trailing}`
  }

  const result = translatePattern(language, trimmed, dictionary)
  if (result) return `${leading}${result}${trailing}`

  const termTranslated = translateTerms(language, trimmed)
  return termTranslated !== trimmed ? `${leading}${termTranslated}${trailing}` : phrase
}

function translatePattern(language, phrase, dictionary) {
  const languageName = dictionary[phrase]
  if (languageName) return languageName

  const countMatch = phrase.match(/^(\d+)\s+(subjects?|books?|chapters?|topics?|questions?|characters?|pending)$/i)
  if (countMatch) {
    const [, count, noun] = countMatch
    return `${count} ${translateNoun(language, noun.toLowerCase())}`
  }

  const markerSentence = phrase.match(/^(\d+)\s+chapter markers across\s+(\d+)\s+pages with\s+(\d+)\s+total TOC entries\.$/i)
  if (markerSentence) {
    const [, chapters, pages, entries] = markerSentence
    return language === 'hi'
      ? `${chapters} अध्याय चिह्न, ${pages} पृष्ठों में, ${entries} कुल विषय-सूची प्रविष्टियों के साथ.`
      : `${chapters} ಅಧ್ಯಾಯ ಗುರುತುಗಳು, ${pages} ಪುಟಗಳಲ್ಲಿ, ${entries} ಒಟ್ಟು ವಿಷಯಸೂಚಿ ನಮೂದುಗಳೊಂದಿಗೆ.`
  }

  const pageMatch = phrase.match(/^Page\s+(.+)$/i)
  if (pageMatch) {
    return language === 'hi' ? `पृष्ठ ${pageMatch[1]}` : `ಪುಟ ${pageMatch[1]}`
  }

  const levelMatch = phrase.match(/^Level\s+(.+)$/i)
  if (levelMatch) {
    return language === 'hi' ? `स्तर ${levelMatch[1]}` : `ಮಟ್ಟ ${levelMatch[1]}`
  }

  const deepestMatch = phrase.match(/^Deepest level\s+(.+)$/i)
  if (deepestMatch) {
    return language === 'hi' ? `सबसे गहरा स्तर ${deepestMatch[1]}` : `ಅತ್ಯಂತ ಆಳವಾದ ಮಟ್ಟ ${deepestMatch[1]}`
  }

  const subtopicMatch = phrase.match(/^(\d+)\s+subtopics?$/i)
  if (subtopicMatch) {
    return language === 'hi' ? `${subtopicMatch[1]} उप-विषय` : `${subtopicMatch[1]} ಉಪವಿಷಯಗಳು`
  }

  const genericCount = phrase.match(/^(\d+)\s+(matches|extracted nodes|root sections|root chapters|terminal nodes|roots|points|tracked topics|attempts)$/i)
  if (genericCount) {
    const [, count, label] = genericCount
    return `${count} ${translateTerms(language, label.toLowerCase())}`
  }

  const percentValue = phrase.match(/^(\d+)%\s+(intensity|average mastery)$/i)
  if (percentValue) {
    const [, value, label] = percentValue
    return `${value}% ${translateTerms(language, label.toLowerCase())}`
  }

  const practiceMatch = phrase.match(/^Practice\s+(section|topic)$/i)
  if (practiceMatch) {
    return language === 'hi'
      ? `${practiceMatch[1].toLowerCase() === 'section' ? 'सेक्शन' : 'टॉपिक'} अभ्यास करें`
      : `${practiceMatch[1].toLowerCase() === 'section' ? 'ವಿಭಾಗ' : 'ವಿಷಯ'} ಅಭ್ಯಾಸ ಮಾಡಿ`
  }

  const noChapterMatch = phrase.match(/^No chapter titles matched "(.+)"\.$/)
  if (noChapterMatch) {
    return language === 'hi'
      ? `"${noChapterMatch[1]}" से कोई अध्याय शीर्षक मेल नहीं खाया.`
      : `"${noChapterMatch[1]}" ಗೆ ಯಾವುದೇ ಅಧ್ಯಾಯ ಶೀರ್ಷಿಕೆ ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ.`
  }

  const classSubjects = phrase.match(/^(.+)\s+Subjects$/)
  if (classSubjects) {
    return language === 'hi'
      ? `${classSubjects[1]} विषय`
      : `${classSubjects[1]} ವಿಷಯಗಳು`
  }

  const resultsFor = phrase.match(/^Results for\s+(.+)$/)
  if (resultsFor) {
    return language === 'hi'
      ? `${resultsFor[1]} के परिणाम`
      : `${resultsFor[1]} ಫಲಿತಾಂಶಗಳು`
  }

  const continueClass = phrase.match(/^Continue into subject distribution, document coverage, and chapter maps for (.+)\.$/)
  if (continueClass) {
    return language === 'hi'
      ? `${continueClass[1]} के लिए विषय वितरण, दस्तावेज़ कवरेज और अध्याय मानचित्र पर आगे बढ़ें.`
      : `${continueClass[1]} ಗಾಗಿ ವಿಷಯ ವಿತರಣೆ, ದಾಖಲೆ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಅಧ್ಯಾಯ ನಕ್ಷೆಗಳಿಗೆ ಮುಂದುವರಿಯಿರಿ.`
  }

  const noSubjects = phrase.match(/^No subjects matched "(.+)"\.$/)
  if (noSubjects) {
    return language === 'hi'
      ? `"${noSubjects[1]}" से कोई विषय मेल नहीं खाया.`
      : `"${noSubjects[1]}" ಗೆ ಯಾವುದೇ ವಿಷಯ ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ.`
  }

  const range = phrase.match(/^(\d+)\s+to\s+(\d+)$/)
  if (range) {
    return language === 'hi'
      ? `${range[1]} से ${range[2]}`
      : `${range[1]} ರಿಂದ ${range[2]}`
  }

  return null
}

function translateTerms(language, phrase) {
  const terms = termTranslations[language]
  if (!terms || !phrase) return phrase

  return Object.entries(terms)
    .sort(([left], [right]) => right.length - left.length)
    .reduce((current, [source, translated]) => {
      const escaped = escapeRegExp(source)
      const pattern = /^[A-Za-z0-9 ]+$/.test(source)
        ? new RegExp(`(?<![\\p{L}\\p{N}])${escaped}(?![\\p{L}\\p{N}])`, 'giu')
        : new RegExp(escaped, 'gu')
      return current.replace(pattern, translated)
    }, phrase)
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function translateNoun(language, noun) {
  const nouns = {
    hi: {
      subject: 'विषय',
      subjects: 'विषय',
      book: 'पुस्तक',
      books: 'पुस्तकें',
      chapter: 'अध्याय',
      chapters: 'अध्याय',
      topic: 'विषय',
      topics: 'विषय',
      question: 'प्रश्न',
      questions: 'प्रश्न',
      character: 'अक्षर',
      characters: 'अक्षर',
      pending: 'लंबित',
    },
    kn: {
      subject: 'ವಿಷಯ',
      subjects: 'ವಿಷಯಗಳು',
      book: 'ಪುಸ್ತಕ',
      books: 'ಪುಸ್ತಕಗಳು',
      chapter: 'ಅಧ್ಯಾಯ',
      chapters: 'ಅಧ್ಯಾಯಗಳು',
      topic: 'ವಿಷಯ',
      topics: 'ವಿಷಯಗಳು',
      question: 'ಪ್ರಶ್ನೆ',
      questions: 'ಪ್ರಶ್ನೆಗಳು',
      character: 'ಅಕ್ಷರ',
      characters: 'ಅಕ್ಷರಗಳು',
      pending: 'ಬಾಕಿ',
    },
  }

  return nouns[language]?.[noun] ?? noun
}
