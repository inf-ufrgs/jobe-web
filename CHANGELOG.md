# Changelog

All notable changes to this project will be documented in this file.

## [1.11] - 2026-03-10

### Added
- **Moodle Integration**: Professors can now import student submissions directly from Moodle by providing a course ID and a web-service token. The system automatically maps students and matches Moodle assignments to local grader assignments using name normalization (Closes #9).

## [1.10] - 2026-03-06

### Fixed
- **Leading Zeros in IDs**: Allow students and professors to log in disregarding leading zeros in their IDs (Closes #7).
- **Line numbers in error messages**: Subtracted the number of lines injected by the input wrapper (`MOCK_WRAPPER`) from all `line N` references in Jobe's error output, so reported line numbers now correctly point to the student's original code (Closes #2).

## [1.9] - 2026-02-20

### Added
- **Visual Colored Diff**: Integrated `diff2html` to display a side-by-side, visually colored diff of expected vs. actual output for student submissions, making debugging easier.
- **Background Repository Sync**: The grader application now autonomously detects new commits to the assignments git repository and updates itself periodically in the background.

### Fixed
- **Assignment Page Header**: Fixed the layout issues in the header of the assignments page.
- **Submission Raw Logs**: Hidden the raw execution logs by default on the results page, adding a toggle button to reveal them only when needed for a cleaner interface.
