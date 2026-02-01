//! Configuration module for environment variables and settings

use anyhow::{Context, Result};
use std::env;
use std::path::PathBuf;
use tracing::info;

/// Application configuration
#[derive(Debug, Clone)]
pub struct Config {
    /// Path to Google Cloud credentials JSON file
    pub credentials_path: Option<String>,
    
    /// Google Cloud project ID
    pub project_id: String,
    
    /// Optional time limit for queries (YYYY-MM-DD format)
    pub limit_time: Option<String>,
}

impl Config {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self> {
        // Try to load .env file from various locations
        Self::load_dotenv();

        let credentials_path = env::var("GOOGLE_APPLICATION_CREDENTIALS").ok();
        
        let project_id = env::var("GCP_PROJECT_ID")
            .context("GCP_PROJECT_ID environment variable is required")?;
        
        let limit_time = env::var("LIMIT_TIME").ok();

        info!("Configuration loaded:");
        info!("  - Project ID: {}", project_id);
        info!("  - Credentials: {}", credentials_path.as_deref().unwrap_or("default"));
        info!("  - Limit Time: {}", limit_time.as_deref().unwrap_or("none"));

        Ok(Self {
            credentials_path,
            project_id,
            limit_time,
        })
    }

    /// Load .env files from various locations
    fn load_dotenv() {
        // Get the executable's directory
        let current_dir = env::current_dir().unwrap_or_default();
        
        // Try parent .env (for Docker Compose)
        let parent_env = current_dir.join("../.env");
        if parent_env.exists() {
            dotenvy::from_path(&parent_env).ok();
            info!("Loaded .env from: {:?}", parent_env);
        }
        
        // Try local .env
        let local_env = current_dir.join(".env");
        if local_env.exists() {
            dotenvy::from_path(&local_env).ok();
            info!("Loaded .env from: {:?}", local_env);
        }

        // Also check the keys directory for credentials
        // Override the GOOGLE_APPLICATION_CREDENTIALS if it doesn't exist
        if let Ok(creds_path) = env::var("GOOGLE_APPLICATION_CREDENTIALS") {
            let creds = PathBuf::from(&creds_path);
            if !creds.exists() {
                // Try to find the credentials in alternative locations
                let alt_paths = [
                    current_dir.join("keys/bigquery.json"),
                    current_dir.join("../mcp-server/keys/bigquery.json"),
                    current_dir.join("../mcp-server-rust/keys/bigquery.json"),
                ];
                
                for alt_path in &alt_paths {
                    if alt_path.exists() {
                        env::set_var("GOOGLE_APPLICATION_CREDENTIALS", alt_path.to_string_lossy().to_string());
                        info!("Credentials file {} not found, using: {:?}", creds_path, alt_path);
                        break;
                    }
                }
            }
        } else {
            // No credentials set, try to find one
            let keys_dir = current_dir.join("keys");
            if keys_dir.exists() {
                let bigquery_key = keys_dir.join("bigquery.json");
                if bigquery_key.exists() {
                    env::set_var("GOOGLE_APPLICATION_CREDENTIALS", bigquery_key.to_string_lossy().to_string());
                    info!("Set GOOGLE_APPLICATION_CREDENTIALS from keys/bigquery.json");
                }
            }
        }
    }

    /// Get credentials path, trying multiple locations
    pub fn get_credentials_path(&self) -> Option<PathBuf> {
        if let Some(ref path) = self.credentials_path {
            let p = PathBuf::from(path);
            if p.exists() {
                return Some(p);
            }
        }

        // Try default locations
        let current_dir = env::current_dir().unwrap_or_default();
        
        let locations = [
            current_dir.join("keys/bigquery.json"),
            current_dir.join("../keys/bigquery.json"),
        ];

        for loc in &locations {
            if loc.exists() {
                return Some(loc.clone());
            }
        }

        None
    }
}

/// Get an environment variable with an optional default
pub fn get_env(key: &str, default: Option<&str>) -> Option<String> {
    env::var(key).ok().or_else(|| default.map(|s| s.to_string()))
}
