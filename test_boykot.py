import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
import time
import tempfile
import csv
import logging

# Add the directory containing boykot.py to sys.path
# Assumes test_boykot.py is in the same directory as boykot.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Attempt to import functions from boykot.py
# These are functions that seem less coupled to the main CLI logic or Instagrapi client
try:
    from boykot import (
        read_blacklist,
        extract_username,
        validate_username,
        load_api_requests, # Assuming this can be imported
        save_api_requests, # Assuming this can be imported
        cleanup_api_requests, # Assuming this can be imported
        record_api_request, # Assuming this can be imported
        check_rate_limit, # Assuming this can be imported
        API_LOG_FILE # Constant
    )
    # For functions that use the global 'api_requests' list in boykot.py,
    # we might need to patch 'boykot.api_requests' directly in tests.
except ImportError as e:
    print(f"CONTINUING WITH PLACEHOLDERS: Error importing from boykot: {e}. Ensure boykot.py is in the same directory.")
    # Define placeholders if import fails, so the test file itself is valid Python
    API_LOG_FILE = "api_request_log.json"
    def read_blacklist(file_path):
        if not os.path.exists(file_path): raise FileNotFoundError
        return []
    def extract_username(input_value): return input_value.split('/')[-1] if '/' in input_value else input_value
    def validate_username(username):
        if not username or len(username) > 30: raise ValueError("Invalid username")
        return username
    def load_api_requests(): return []
    def save_api_requests(timestamps): pass
    def cleanup_api_requests(): global api_requests; api_requests = []; return api_requests
    def record_api_request(): global api_requests; api_requests.append(time.time()); return len(api_requests)
    def check_rate_limit(remaining_to_block, request_limit): pass
    # Dummy global for placeholder functions
    api_requests = []


class TestBoykotScript(unittest.TestCase):

    def setUp(self):
        # Suppress logging output during tests unless specifically testing logging
        logging.disable(logging.CRITICAL)
        self.temp_dir = tempfile.TemporaryDirectory()
        # Mock boykot.api_requests for tests that modify it, to avoid state leakage
        self.patcher = patch('boykot.api_requests', [])
        self.mock_api_requests = self.patcher.start()


    def tearDown(self):
        self.temp_dir.cleanup()
        logging.disable(logging.NOTSET)
        self.patcher.stop()


    # Test extract_username
    def test_extract_username_url(self):
        self.assertEqual(extract_username("http://instagram.com/testuser/"), "testuser")
        self.assertEqual(extract_username("https://www.instagram.com/test_user_123"), "test_user_123")

    def test_extract_username_plain(self):
        self.assertEqual(extract_username("testuser"), "testuser")

    def test_extract_username_empty(self):
        self.assertEqual(extract_username(""), "") # Actual behavior is to return the input if not URL

    # Test validate_username
    def test_validate_username_valid(self):
        self.assertEqual(validate_username("testuser"), "testuser")
        self.assertEqual(validate_username("test.user_123"), "test.user_123")

    def test_validate_username_invalid_chars(self):
        with self.assertRaises(ValueError):
            validate_username("test-user!")

    def test_validate_username_too_long(self):
        with self.assertRaises(ValueError):
            validate_username("a" * 31)

    def test_validate_username_empty(self):
        with self.assertRaises(ValueError):
            validate_username("")

    # Test read_blacklist
    def test_read_blacklist_txt_valid(self):
        txt_path = os.path.join(self.temp_dir.name, "blacklist.txt")
        with open(txt_path, "w") as f:
            f.write("user1\nuser2\nuser.3\n")
        # Patch validate_username to be a pass-through for this test's focus
        with patch('boykot.validate_username', side_effect=lambda x: x) as mock_validate:
            users = read_blacklist(txt_path)
            self.assertEqual(users, ["user1", "user2", "user.3"])
            self.assertEqual(mock_validate.call_count, 3)

    def test_read_blacklist_csv_valid(self):
        csv_path = os.path.join(self.temp_dir.name, "blacklist.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "other_column"])
            writer.writerow(["userA", "data1"])
            writer.writerow(["userB", "data2"])
        with patch('boykot.validate_username', side_effect=lambda x: x) as mock_validate:
            users = read_blacklist(csv_path)
            self.assertEqual(users, ["userA", "userB"])
            self.assertEqual(mock_validate.call_count, 2)

    @patch('logging.error')
    def test_read_blacklist_file_not_found(self, mock_log_error):
        # The function is designed to catch FileNotFoundError and log an error, then return empty list.
        result = read_blacklist("nonexistentfile.txt")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once() # Check that logging.error was called

    # Test API Log functions
    @patch('boykot.API_LOG_FILE', 'test_api_log.json') # Use a test-specific log file name
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_api_requests_file_not_found(self, mock_file_open, mock_os_exists):
        mock_os_exists.return_value = False
        # Ensure boykot.api_requests is reset if load_api_requests modifies it globally
        with patch('boykot.api_requests', []):
            self.assertEqual(load_api_requests(), [])
        mock_os_exists.assert_called_with('test_api_log.json')

    @patch('boykot.API_LOG_FILE', 'test_api_log.json')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_api_requests_invalid_json(self, mock_json_load, mock_file_open, mock_os_exists):
        mock_os_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Error", "doc", 0)
        with patch('logging.error') as mock_log_error: # boykot.py uses logging.error
             with patch('boykot.api_requests', []):
                self.assertEqual(load_api_requests(), [])
        mock_log_error.assert_called()

    @patch('boykot.API_LOG_FILE', 'test_api_log.json')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[1678886400, 1678886500]')
    def test_load_api_requests_valid(self, mock_file_open, mock_os_exists):
        mock_os_exists.return_value = True
        with patch('boykot.api_requests', []):
            self.assertEqual(load_api_requests(), [1678886400, 1678886500])

    @patch('boykot.API_LOG_FILE', 'test_api_log.json')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_api_requests(self, mock_json_dump, mock_file_open):
        test_data = [1678886400, 1678886500]
        save_api_requests(test_data)
        mock_file_open.assert_called_with('test_api_log.json', "w", encoding="utf-8")
        mock_json_dump.assert_called_with(test_data, mock_file_open())

    def test_cleanup_api_requests(self):
        current_time = time.time()
        initial_list_content = [current_time - 3700, current_time - 1000, current_time - 500]
        self.mock_api_requests[:] = initial_list_content # Set the content of the patched list

        # Import boykot here to access the *current* state of its members after potential rebinding
        import boykot 
        
        expected_cleaned_list = [t for t in initial_list_content if current_time - t < 3600]

        with patch('boykot.save_api_requests') as mock_save:
            # Call the actual function from the boykot module
            returned_requests = boykot.cleanup_api_requests()

            # 1. Check the return value
            self.assertEqual(returned_requests, expected_cleaned_list)
            
            # 2. Check that the global 'boykot.api_requests' (which was patched)
            # now refers to the new list with the cleaned content.
            self.assertEqual(boykot.api_requests, expected_cleaned_list)
            
            # 3. Check that save_api_requests was called with the new list
            mock_save.assert_called_with(expected_cleaned_list)

    def test_record_api_request(self):
        self.mock_api_requests[:] = [] # Ensure it's empty before test
        start_time = time.time()
        with patch('boykot.cleanup_api_requests', return_value=self.mock_api_requests) as mock_cleanup:
             # boykot.py calls cleanup_api_requests
            count = record_api_request()
        end_time = time.time()
        self.assertEqual(count, 1)
        self.assertEqual(len(self.mock_api_requests), 1)
        self.assertTrue(start_time <= self.mock_api_requests[0] <= end_time)
        mock_cleanup.assert_called_once()

    @patch('time.sleep') # To prevent actual sleeping
    @patch('logging.info') # To check log messages
    def test_check_rate_limit_under_limit(self, mock_log_info, mock_time_sleep):
        self.mock_api_requests[:] = [time.time() - 100] * 5 # 5 recent requests
        # Call with a limit of 10, remaining_to_block doesn't matter if under limit
        check_rate_limit(remaining_to_block=20, request_limit=10)
        mock_time_sleep.assert_not_called() # Should not sleep

    @patch('time.sleep')
    @patch('logging.info')
    @patch('boykot.save_api_requests') # cleanup_api_requests calls this, so mock it
    @patch('boykot.cleanup_api_requests') # Mocking cleanup to control the global list state precisely
    def test_check_rate_limit_over_limit_then_recovers(self, mock_boykot_cleanup, mock_boykot_save_api, mock_log_info, mock_time_sleep):
        current_time = time.time()
        request_limit = 10
        
        # Define states for boykot.api_requests (which is self.mock_api_requests in the test)
        over_limit_state = [current_time - i * 10 for i in range(15)] # 15 requests
        under_limit_state = [current_time - i * 10 for i in range(request_limit // 2 - 1)] # 4 requests

        # This function will be the side_effect of the mocked boykot.cleanup_api_requests
        def cleanup_side_effect_function():
            # On the 1st (initial check) and 2nd call (first loop iteration), simulate "over limit"
            if mock_boykot_cleanup.call_count <= 2:
                self.mock_api_requests[:] = over_limit_state 
            # On the 3rd call (second loop iteration), simulate "under limit" for recovery
            else:
                self.mock_api_requests[:] = under_limit_state
            
            # The real cleanup_api_requests calls save_api_requests and returns the list.
            # We need our mock to simulate this part of its contract if check_rate_limit uses the return value,
            # or if save_api_requests has side effects we need to control (here, just ensuring it's callable).
            save_api_requests(self.mock_api_requests) # Simulate the call to save (it's imported directly)
            return self.mock_api_requests # Return the current state of the patched global list

        mock_boykot_cleanup.side_effect = cleanup_side_effect_function
        
        # Set the initial state for boykot.api_requests before check_rate_limit is called.
        # The first call to the mocked cleanup_api_requests will then establish the 'over_limit_state'.
        self.mock_api_requests[:] = over_limit_state
        
        # Call the function under test. Set remaining_to_block to a value that ensures
        # the rate limit is primarily dictated by request_limit for the "over limit" part of the test.
        # If current_count (15) > remaining_to_block, then this part of OR condition is false.
        check_rate_limit(remaining_to_block=5, request_limit=request_limit)

        # Assertions
        self.assertGreaterEqual(mock_time_sleep.call_count, 1) # Should have slept at least once
        # Check for specific log messages
        # Note: Using mock_log_info.call_args_list to check all calls
        logged_messages = [call[0][0] for call in mock_log_info.call_args_list]
        self.assertIn(f"Son 1 saat içinde {request_limit} API isteği yapıldı. Engelleme işlemleri durduruluyor, lütfen bekleyin...", logged_messages)
        self.assertIn("API isteği sayısı sınırın yarısına veya engellenecek hesap sayısına düştü. Engelleme işlemlerine devam ediliyor.", logged_messages)


if __name__ == '__main__':
    unittest.main()
