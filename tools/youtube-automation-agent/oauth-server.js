const express = require('express');
const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function esc(v) { return String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;'); }
const chalk = require('chalk');

class OAuthServer {
  constructor() {
    this.app = express();
    this.server = null;
    this.expectedState = null;
    this.setupRoutes();
  }

  setupRoutes() {
    this.app.get('/auth/callback', async (req, res) => {
      const { code, error, state } = req.query;

      // The port is reachable by anything running on this machine, so a
      // callback is only accepted when it carries the state this run issued.
      if (!this.stateMatches(state)) {
        res.status(400).send('<h1>❌ Authorization Rejected</h1><p>The callback did not match the authorization request this process started.</p>');
        return;
      }
      this.expectedState = null;

      if (error) {
        res.send(`<h1>❌ Authentication Error</h1><p>${esc(error)}</p>`);
        return;
      }

      if (!code) {
        res.send(`<h1>❌ No Authorization Code</h1><p>No authorization code received</p>`);
        return;
      }

      try {
        // Exchange code for tokens
        await this.exchangeCodeForTokens(code);
        
        res.send(`
          <h1>🎉 Authentication Successful!</h1>
          <p>Your YouTube Automation Agent has been successfully authorized!</p>
          <p>You can close this window and return to the terminal.</p>
          <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            h1 { color: #4CAF50; }
          </style>
        `);
        
        console.log(chalk.green('\n✅ Authentication successful! Starting YouTube Automation Agent...'));
        
        // Close the server after successful auth
        setTimeout(() => {
          this.server.close();
          this.startMainApplication();
        }, 2000);
        
      } catch (error) {
        console.error(chalk.red('Token exchange failed:'), error);
        res.send(`<h1>❌ Token Exchange Failed</h1><p>${esc(error.message)}</p>`);
      }
    });

    this.app.get('/', (req, res) => {
      res.send(`
        <h1>🎬 YouTube Automation Agent</h1>
        <p>OAuth callback server is running...</p>
        <p>Please complete the authorization process.</p>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        </style>
      `);
    });
  }

  // A fresh random state per authorization request, never reused.
  createState() {
    this.expectedState = crypto.randomBytes(32).toString('hex');
    return this.expectedState;
  }

  stateMatches(received) {
    const expected = this.expectedState;
    if (!expected || typeof received !== 'string' || received.length !== expected.length) {
      return false;
    }
    return crypto.timingSafeEqual(Buffer.from(received), Buffer.from(expected));
  }

  async exchangeCodeForTokens(code) {
    const credentialsPath = path.join(__dirname, 'config', 'credentials.json');
    const tokensPath = path.join(__dirname, 'config', 'tokens.json');
    
    const credentials = JSON.parse(fs.readFileSync(credentialsPath));
    
    const oauth2Client = new google.auth.OAuth2(
      credentials.youtube.client_id,
      credentials.youtube.client_secret,
      credentials.youtube.redirect_uris[0]
    );

    const { tokens } = await oauth2Client.getToken(code);
    
    // Save tokens
    const tokenData = {
      youtube: tokens
    };
    
    fs.writeFileSync(tokensPath, JSON.stringify(tokenData, null, 2), { mode: 0o600 });
    fs.chmodSync(tokensPath, 0o600);
    console.log(chalk.green('✅ Tokens saved successfully!'));
  }

  async startMainApplication() {
    console.log(chalk.cyan('\n🚀 Starting YouTube Automation Agent...'));
    
    // Import and start the main application
    const { spawn } = require('child_process');
    const mainApp = spawn('node', ['index.js'], {
      stdio: 'inherit',
      cwd: __dirname
    });
    
    mainApp.on('close', (code) => {
      console.log(chalk.yellow(`Main application exited with code ${code}`));
    });
  }

  start() {
    this.server = this.app.listen(8080, '127.0.0.1', () => {
      console.log(chalk.cyan('\n🔐 OAuth callback server started on http://localhost:8080'));
      this.generateAuthUrl();
    });
  }

  generateAuthUrl() {
    const credentialsPath = path.join(__dirname, 'config', 'credentials.json');
    const credentials = JSON.parse(fs.readFileSync(credentialsPath));
    
    const oauth2Client = new google.auth.OAuth2(
      credentials.youtube.client_id,
      credentials.youtube.client_secret,
      credentials.youtube.redirect_uris[0]
    );

    const scopes = [
      'https://www.googleapis.com/auth/youtube.upload',
      'https://www.googleapis.com/auth/youtube',
      'https://www.googleapis.com/auth/youtube.readonly',
      'https://www.googleapis.com/auth/yt-analytics.readonly',
      'https://www.googleapis.com/auth/youtube.force-ssl'
    ];

    const authUrl = oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: scopes,
      prompt: 'consent',
      state: this.createState()
    });

    console.log(chalk.cyan.bold('\n🎬 YouTube Automation Agent - OAuth Setup'));
    console.log(chalk.gray('═'.repeat(60)));
    console.log(chalk.cyan('\n🔗 Please visit this URL to authorize the application:'));
    console.log(chalk.blue.underline(authUrl));
    console.log(chalk.yellow('\nAfter authorization, you will be redirected back automatically.'));
    console.log(chalk.gray('The OAuth server will handle the rest!'));
  }
}

if (require.main === module) {
  const oauthServer = new OAuthServer();
  oauthServer.start();
}

module.exports = { OAuthServer };
