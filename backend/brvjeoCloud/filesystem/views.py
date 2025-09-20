from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView


class FileUploadView(APIView):
    def post(self, request):
        return Response({"message": "File uploaded"}, status=status.HTTP_201_CREATED)


class FileListView(APIView):
    def get(self, request):
        return Response({"files": []}, status=status.HTTP_200_OK)


class FileDownloadView(APIView):
    def get(self, request, pk):
        return Response({"message": f"Downloading file {pk}"}, status=status.HTTP_200_OK)


class FilePreviewView(APIView):
    def get(self, request, pk):
        return Response({"message": f"Preview for file {pk}"}, status=status.HTTP_200_OK)


class FileDeleteView(APIView):
    def delete(self, request, pk):
        return Response({"message": f"File {pk} deleted"}, status=status.HTTP_204_NO_CONTENT)


class FileShareView(APIView):
    def post(self, request, pk):
        return Response({"message": f"File {pk} shared"}, status=status.HTTP_200_OK)


class FileMoveView(APIView):
    def post(self, request, pk):
        return Response({"message": f"File {pk} moved"}, status=status.HTTP_200_OK)


class FileBulkUploadView(APIView):
    def post(self, request):
        return Response({"message": "Bulk upload complete"}, status=status.HTTP_201_CREATED)


class FolderCreateView(APIView):
    def post(self, request):
        return Response({"message": "Folder created"}, status=status.HTTP_201_CREATED)


class PublicSharedFileView(APIView):
    def get(self, request, token):
        return Response({"message": f"Public file with token {token}"}, status=status.HTTP_200_OK)
    

class FileViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"files": []})

    def retrieve(self, request, pk=None):
        return Response({"message": f"Retrieve file {pk}"})


class FolderViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"folders": []})

    def retrieve(self, request, pk=None):
        return Response({"message": f"Retrieve folder {pk}"})