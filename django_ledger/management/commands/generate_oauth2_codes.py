import base64
import hashlib
import json
import random
import string
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates a code challenge and a code verifier used for Authorization Code grants when using OAuth2'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, choices=['stdout', 'json'], default='stdout')

    def handle(self, *args, **options):
        code_verifier = ''.join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(43, 128)))
        code_verifier = base64.urlsafe_b64encode(code_verifier.encode('utf-8'))

        code_challenge = hashlib.sha256(code_verifier).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')

        code_verifier = code_verifier.decode("utf-8")

        if options['output'] == 'stdout':
            self.stdout.write(self.style.SUCCESS(f'Code Verifier: {code_verifier}'))
            self.stdout.write(self.style.SUCCESS(f'Code Challenge: {code_challenge}'))

        elif options['output'] == 'json':
            out_file = Path(settings.BASE_DIR).joinpath('oauth_codes.json')

            codes = {
                'code_verifier': code_verifier,
                'code_challenge': code_challenge
            }

            with open(out_file, 'w') as io:
                json.dump(codes, io, indent=4)
