from django.contrib.auth.password_validation import UserAttributeSimilarityValidator, MinimumLengthValidator, CommonPasswordValidator, NumericPasswordValidator
from django.core.exceptions import ValidationError

class CombinedPasswordValidator:
    def validate(self, password, user=None):
        validators = [
            UserAttributeSimilarityValidator(),
            MinimumLengthValidator(),
            CommonPasswordValidator(),
            NumericPasswordValidator(),
        ]
        
        for validator in validators:
            try:
                validator.validate(password, user)
            except ValidationError:
                raise ValidationError("Пароль слишком простой")