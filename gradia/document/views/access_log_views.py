from django.views.generic import ListView
from gradia.document.models import DocumentAccessLog
from gradia.document.views.mixins import DocumentManageMixin

class DocumentAccessLogListView(DocumentManageMixin, ListView):
    template_name = "document/access_logs.html"
    context_object_name = "logs"
    paginate_by = 30
    
    def get_queryset(self):
        return DocumentAccessLog.objects.select_related('user', 'document').order_by('-accessed_at')
