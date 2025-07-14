-- Create a dedicated user for the application
CREATE USER a2a WITH PASSWORD 'a2a_password';

-- Create the tasks database
CREATE DATABASE a2a_tasks;

GRANT ALL PRIVILEGES ON DATABASE a2a_test TO a2a;

