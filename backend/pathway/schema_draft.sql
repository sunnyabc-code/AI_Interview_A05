-- Draft schema for isolated pathway module (not applied yet)

CREATE TABLE learning_path_profiles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  technical_score DECIMAL(5,2) NULL,
  expression_score DECIMAL(5,2) NULL,
  dimensions_json JSON NOT NULL,
  weaknesses_json JSON NOT NULL,
  strengths_json JSON NOT NULL,
  confidence_level DECIMAL(5,2) NOT NULL DEFAULT 0,
  snapshot_time DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL
);

CREATE TABLE learning_path_plans (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  profile_id BIGINT NOT NULL,
  status VARCHAR(20) NOT NULL,
  cycle_days INT NOT NULL,
  goal_summary TEXT NOT NULL,
  expected_gain_json JSON NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL
);

CREATE TABLE learning_path_tasks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  plan_id BIGINT NOT NULL,
  day_index INT NOT NULL,
  task_type VARCHAR(20) NOT NULL,
  source_type VARCHAR(30) NOT NULL,
  source_id BIGINT NULL,
  title VARCHAR(300) NOT NULL,
  reason TEXT NOT NULL,
  estimated_minutes INT NOT NULL,
  priority INT NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  completion_note TEXT NOT NULL,
  done_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL
);
