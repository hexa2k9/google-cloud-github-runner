import json
from unittest.mock import patch


class TestWebhookRoutes:
    @patch('app.routes.webhook.verify_github_signature')
    @patch('app.routes.webhook.WebhookService')
    def test_workflow_job_webhook(self, mock_webhook_service, mock_verify, client, sample_workflow_job_payload):
        """Test handling workflow_job webhook."""
        mock_verify.return_value = True
        mock_service_instance = mock_webhook_service.return_value
        mock_service_instance.handle_workflow_job.return_value = {
            "action": "created",
            "runner_name": "runner-abc123"
        }

        response = client.post(
            '/webhook',
            data=json.dumps(sample_workflow_job_payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'workflow_job'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['action'] == 'created'
        assert response.json['runner_name'] == 'runner-abc123'
        mock_service_instance.handle_workflow_job.assert_called_once()

    @patch('app.routes.webhook.verify_github_signature')
    @patch('app.routes.webhook.WebhookService')
    def test_workflow_job_webhook_created_response(self, mock_webhook_service, mock_verify, client):
        """Test that created runner name is included in the response body."""
        mock_verify.return_value = True
        mock_service_instance = mock_webhook_service.return_value
        mock_service_instance.handle_workflow_job.return_value = {
            "action": "created",
            "runner_name": "runner-uuid-12345"
        }

        payload = {
            'action': 'queued',
            'workflow_job': {'labels': ['gcp-ubuntu-24.04']},
            'repository': {
                'html_url': 'https://github.com/owner/repo',
                'full_name': 'owner/repo'
            }
        }

        response = client.post(
            '/webhook',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'workflow_job'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['action'] == 'created'
        assert response.json['runner_name'] == 'runner-uuid-12345'

    @patch('app.routes.webhook.verify_github_signature')
    @patch('app.routes.webhook.WebhookService')
    def test_workflow_job_webhook_deleted_response(self, mock_webhook_service, mock_verify, client):
        """Test that deleted runner name is included in the response body."""
        mock_verify.return_value = True
        mock_service_instance = mock_webhook_service.return_value
        mock_service_instance.handle_workflow_job.return_value = {
            "action": "deleted",
            "runner_name": "runner-12345"
        }

        payload = {
            'action': 'completed',
            'workflow_job': {'runner_name': 'runner-12345'}
        }

        response = client.post(
            '/webhook',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'workflow_job'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['action'] == 'deleted'
        assert response.json['runner_name'] == 'runner-12345'

    @patch('app.routes.webhook.verify_github_signature')
    @patch('app.routes.webhook.WebhookService')
    def test_workflow_job_webhook_ignored_response(self, mock_webhook_service, mock_verify, client):
        """Test that ignored jobs return null runner_name in response body."""
        mock_verify.return_value = True
        mock_service_instance = mock_webhook_service.return_value
        mock_service_instance.handle_workflow_job.return_value = {
            "action": "ignored",
            "runner_name": None
        }

        payload = {
            'action': 'queued',
            'workflow_job': {'labels': ['ubuntu-latest']},
            'repository': {
                'html_url': 'https://github.com/owner/repo',
                'full_name': 'owner/repo'
            }
        }

        response = client.post(
            '/webhook',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'workflow_job'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['action'] == 'ignored'
        assert response.json['runner_name'] is None

    @patch('app.routes.webhook.verify_github_signature')
    def test_installation_webhook(self, mock_verify, client, sample_installation_payload):
        """Test handling installation webhook."""
        mock_verify.return_value = True

        response = client.post(
            '/webhook',
            data=json.dumps(sample_installation_payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'installation'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'ignored'

    @patch('app.routes.webhook.verify_github_signature')
    def test_unknown_webhook_event(self, mock_verify, client):
        """Test handling unknown webhook event."""
        mock_verify.return_value = True
        payload = {'action': 'test'}

        response = client.post(
            '/webhook',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'unknown_event'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'ignored'

    @patch('app.routes.webhook.verify_github_signature')
    @patch('app.routes.webhook.WebhookService')
    def test_workflow_job_webhook_error(self, mock_webhook_service, mock_verify, client, sample_workflow_job_payload):
        """Test error handling in workflow_job webhook."""
        mock_verify.return_value = True
        mock_service_instance = mock_webhook_service.return_value
        mock_service_instance.handle_workflow_job.side_effect = Exception("Processing error")

        response = client.post(
            '/webhook',
            data=json.dumps(sample_workflow_job_payload),
            content_type='application/json',
            headers={'X-GitHub-Event': 'workflow_job'}
        )

        assert response.status_code == 500
        assert response.json['status'] == 'error'
        # Security improvement: we now return generic 'Internal error' instead of exposing the actual error
        assert response.json['message'] == 'Internal error'

    @patch('app.routes.webhook.verify_github_signature')
    def test_webhook_invalid_signature(self, mock_verify, client):
        """Test webhook with invalid signature."""
        mock_verify.return_value = False

        response = client.post(
            '/webhook',
            data=json.dumps({'test': 'data'}),
            content_type='application/json',
            headers={
                'X-GitHub-Event': 'workflow_job',
                'X-Hub-Signature-256': 'invalid'
            }
        )

        assert response.status_code == 403
        assert response.json['status'] == 'forbidden'

    def test_webhook_ping_event(self, client):
        """Test webhook ping event."""
        response = client.post(
            '/webhook',
            data=json.dumps({'zen': 'test'}),
            content_type='application/json',
            headers={'X-GitHub-Event': 'ping'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
